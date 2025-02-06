from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response  # for debugging
import re
import json
from inflection import parameterize, underscore

class CompetitionsSpider(BaseSpider):
    name = 'competitions'
    
    # Removed the old 'international_competitions' dict since we're skipping international comps

    def parse(self, response, parent):
        """
        Parse confederations page to get each country's 'wettbewerbe/national/wettbewerbe/<id>' link.
        This approach does not itself decide tier; that happens later in parse_competitions().
        """
        table_rows = response.css('table.items tbody tr.odd, table.items tbody tr.even')

        for row in table_rows:
            country_image_url = row.xpath('td')[1].css('img::attr(src)').get()
            country_name = row.xpath('td')[1].css('img::attr(title)').get()
            
            # The 'country_code' from here often corresponds to top-tier code (like 'BRA1') 
            # but we'll rename it to 'confed_country_code' to avoid confusion with actual comp code
            temp_country_code = (
                row.xpath('td')[0]
                   .xpath('table/tr/td')[1]
                   .xpath('a/@href').get()
                   .split('/')[-1]
            )

            total_clubs = row.css('td:nth-of-type(3)::text').get()
            total_players = row.css('td:nth-of-type(4)::text').get()
            average_age = row.css('td:nth-of-type(5)::text').get()
            foreigner_percentage = row.css('td:nth-of-type(6) a::text').get()
            total_value = row.css('td:nth-of-type(8)::text').get()

            matches = re.search(r'([0-9]+)\.png', country_image_url, re.IGNORECASE)
            if not matches:
                continue
            country_id = matches.group(1)

            # We'll follow /wettbewerbe/national/wettbewerbe/<country_id> to parse domestic leagues
            href = f"/wettbewerbe/national/wettbewerbe/{country_id}"

            cb_kwargs = {
                'base': {
                    'parent': parent,  # from confederations spider
                    'country_id': country_id,
                    'country_name': country_name,
                    'confed_country_code': temp_country_code,  # rename, to avoid confusion
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
        Parse 'Domestic leagues & cups', ignoring 'Domestic Cup' / 'Domestic Super Cup' 
        and ignoring the 'International competitions' box altogether.
        
        We'll parse the actual competition code from each link so second-tier has 'BRA2', etc.
        """
        domestic_competitions_tag = 'Domestic leagues & cups'
        boxes = response.css('div.box')
        
        relevant_box = None
        for box in boxes:
            box_header = self.safe_strip(box.css('h2.content-box-headline::text').get())
            if box_header == domestic_competitions_tag:
                relevant_box = box
                break

        if not relevant_box:
            return  # no domestic box found, skip

        box_body = relevant_box.xpath('div[@class="responsive-table"]//tbody')[0]
        box_rows = box_body.xpath('tr')

        # We'll parse row pairs: row N is the tier name, row N+1 has the link
        idx = 0
        while idx < len(box_rows):
            tier_row = box_rows[idx]
            tier_name = tier_row.xpath('td/text()').get() or ""
            
            # Skip if it's Domestic Cup or Domestic Super Cup
            if tier_name not in ("Domestic Cup", "Domestic Super Cup"):
                # Next row often has the actual comp link
                link_row_idx = idx + 1
                if link_row_idx < len(box_rows):
                    link_row = box_rows[link_row_idx]
                    competition_href = link_row.xpath('td/table//td')[1].xpath('a/@href').get()
                    if competition_href:
                        # Extract the real code from the link, e.g. 'BRA2' 
                        # ignoring any trailing slash or season id
                        match_code = re.search(r'/wettbewerb/([^/]+)$', competition_href)
                        competition_code = match_code.group(1) if match_code else None

                        parameterized_tier = underscore(parameterize(tier_name))

                        yield {
                            'type': 'competition',
                            # bring over everything from base, except we rename 'country_code'
                            **base,
                            # set actual competition code
                            'competition_code': competition_code,  
                            'competition_type': parameterized_tier,
                            'href': competition_href
                        }
            idx += 2

    def closed(self, reason):
        """
        We skip any logic about international competitions or printing them.
        Because we only care about domestic leagues of all tiers 
        and ignoring cups & super cups.
        """
        pass

