from tfmkt.spiders.common_comp_club import BaseSpider
import re
from inflection import parameterize, underscore

class CompetitionsSpider(BaseSpider):
    name = 'competitions'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_competitions = set()

    def parse(self, response, parent):
        """
        Parse confederations page. For each row (country), follow
        the link to /wettbewerbe/national/wettbewerbe/<country_id>
        but do NOT store the old 'country_code' from the table row.
        """
        table_rows = response.css('table.items tbody tr.odd, table.items tbody tr.even')

        for row in table_rows:
            country_image_url = row.xpath('td')[1].css('img::attr(src)').get()
            country_name = row.xpath('td')[1].css('img::attr(title)').get()

            total_clubs = row.css('td:nth-of-type(3)::text').get()
            total_players = row.css('td:nth-of-type(4)::text').get()
            average_age = row.css('td:nth-of-type(5)::text').get()
            foreigner_percentage = row.css('td:nth-of-type(6) a::text').get()
            total_value = row.css('td:nth-of-type(8)::text').get()

            # Extract the numeric <country_id> from the .png
            match = re.search(r'([0-9]+)\.png', country_image_url, re.IGNORECASE)
            if not match:
                continue
            country_id = match.group(1)

            href = f"/wettbewerbe/national/wettbewerbe/{country_id}"

            cb_kwargs = {
                'base': {
                    'parent': parent,
                    'country_id': country_id,
                    'country_name': country_name,
                    'total_clubs': total_clubs,
                    'total_players': total_players,
                    'average_age': average_age,
                    'foreigner_percentage': foreigner_percentage,
                    'total_value': total_value
                }
            }

            yield response.follow(self.base_url + href, self.parse_competitions, cb_kwargs=cb_kwargs)

    def parse_competitions(self, response, base):
        """
        Parse domestic leagues from the 'Domestic leagues & cups' box,
        skipping 'Domestic Cup' and 'Domestic Super Cup.'
        Extract the real 'competition_code' from each link (like 'BRA2'),
        store competition_type from the tier name (like 'second_tier').
        """
        domestic_tag = 'Domestic leagues & cups'
        boxes = response.css('div.box')
        relevant_box = None
        for box in boxes:
            box_header = self.safe_strip(box.css('h2.content-box-headline::text').get())
            if box_header == domestic_tag:
                relevant_box = box
                break

        if not relevant_box:
            return

        box_body = relevant_box.xpath('div[@class="responsive-table"]//tbody')[0]
        box_rows = box_body.xpath('tr')

        idx = 0
        while idx < len(box_rows):
            tier_row = box_rows[idx]
            tier_name = tier_row.xpath('td/text()').get() or ""

            # skip cups
            if tier_name not in ("Domestic Cup", "Domestic Super Cup"):
                link_row_idx = idx + 1
                if link_row_idx < len(box_rows):
                    link_row = box_rows[link_row_idx]
                    competition_href = link_row.xpath('td/table//td')[1].xpath('a/@href').get()
                    if competition_href:
                        # e.g. /campeonato-brasileiro-serie-b/startseite/wettbewerb/BRA2
                        # extract 'BRA2'
                        if competition_href in ('/liguilla-clausura/startseite/wettbewerb/POME', '/liguilla-apertura/startseite/wettbewerb/POMX', '/liga-mx-apertura/startseite/wettbewerb/MEXA'):
                            competition_href = '/liga-mx-clausura/startseite/wettbewerb/MEX1'
                        if competition_href in ('/torneo-clausura/startseite/wettbewerb/ARGC'):
                            competition_href = '/torneo-apertura/startseite/wettbewerb/ARG1'
                        match_code = re.search(r'/wettbewerb/([^/]+)$', competition_href)
                        competition_code = match_code.group(1) if match_code else None

                        # Create a unique key for the competition
                        competition_key = f"{base['country_id']}_{competition_code}"
                        
                        # Only yield if we haven't seen this competition before
                        if competition_key not in self.seen_competitions:
                            self.seen_competitions.add(competition_key)
                            parameterized_tier = underscore(parameterize(tier_name))

                            yield {
                                'type': 'competition',
                                **base,  # merges country_id, country_name, etc.
                                'competition_code': competition_code,
                                'competition_type': parameterized_tier,
                                'href': competition_href
                            }
            idx += 2

        # Manually add competitions that aren't scraped
        
        manual_competitions = [
                {
                    'href': '/national-league-south/startseite/wettbewerb/NLS6',
                    'code': 'NLS6',
                    'type': 'national_league_south'
                },
                {
                    'href': '/national-league-north/startseite/wettbewerb/NLN6',
                    'code': 'NLN6',
                    'type': 'national_league_north'
                },
                {
                    'href': '/premier-league-2/startseite/wettbewerb/GB21',
                    'code': 'GB21',
                    'type': 'premier_league_2'
                },
                {
                    'href': '/u18-premier-league/startseite/wettbewerb/GB18',
                    'code': 'GB18',
                    'type': 'u18_premier_league'
                }
            ]

        for comp in manual_competitions:
            competition_key = f"189_{comp['code']}"
            if competition_key not in self.seen_competitions:
                self.seen_competitions.add(competition_key)
                yield {
                        'type': 'competition',
                        **base,
                        'competition_code': comp['code'],
                        'competition_type': comp['type'],
                        'href': comp['href']
                    }

    def closed(self, reason):
        # ignoring international comps entirely
        pass
