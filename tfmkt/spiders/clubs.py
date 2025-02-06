import re
from urllib.parse import unquote, urlparse
from tfmkt.spiders.common import BaseSpider

class ClubsSpider(BaseSpider):
    name = 'clubs'

    def parse(self, response, parent):
        """
        Parse a competition page. We collect all teams from each 'club' table.
        Some competitions might have multiple tables if second-tier is also listed.
        """
        def is_teams_table(table):
            headers = [h.strip().lower() for h in table.css('th::text').getall() if h]
            # We consider it a "teams table" if ANY header cell says "club"
            return any("club" in hdr for hdr in headers)

        def extract_team_href(row):
            """Extract team link from the 2nd <td> in the row."""
            tds = row.css('td')
            if len(tds) >= 2:
                return tds[1].css('a::attr(href)').get()
            return None

        page_tables = response.css('div.responsive-table')
        teams_tables = [tbl for tbl in page_tables if is_teams_table(tbl)]
        
        for table in teams_tables:
            for row in table.css('tbody tr'):
                href = extract_team_href(row)
                if not href:
                    continue

                href_strip_season = re.sub(r'/saison_id/\d{4}$', '', href)
                
                # Merge the parent's data, then override 'type' and 'href' for the club
                base_club = dict(parent)  # copy the competition item
                base_club.update({
                    'type': 'club',
                    'href': href_strip_season
                })

                yield response.follow(
                    href,
                    self.parse_details,
                    cb_kwargs={'base': base_club}
                )

    def parse_details(self, response, base):
        """
        Extract detailed club info from the main page.
        """
        attributes = {}

        # total market value
        attributes['total_market_value'] = response.css('div.dataMarktwert a::text').get()

        # parse "Squad size", "Average age", etc.
        attributes['squad_size'] = self.safe_strip(
            response.xpath("//li[contains(text(),'Squad size:')]/span/text()").get()
        )
        attributes['average_age'] = self.safe_strip(
            response.xpath("//li[contains(text(),'Average age:')]/span/text()").get()
        )

        # foreigners
        foreigners_li = response.xpath("//li[contains(text(),'Foreigners:')]")
        if foreigners_li:
            attributes['foreigners_number'] = self.safe_strip(
                foreigners_li[0].xpath("span/a/text()").get()
            )
            attributes['foreigners_percentage'] = self.safe_strip(
                foreigners_li[0].xpath("span/span/text()").get()
            )
        else:
            attributes['foreigners_number'] = None
            attributes['foreigners_percentage'] = None

        # national team players
        attributes['national_team_players'] = self.safe_strip(
            response.xpath("//li[contains(text(),'National team players:')]/span/a/text()").get()
        )

        # stadium name & seats
        stadium_li = response.xpath("//li[contains(text(),'Stadium:')]")
        if stadium_li:
            attributes['stadium_name'] = self.safe_strip(
                stadium_li[0].xpath("span/a/text()").get()
            )
            attributes['stadium_seats'] = self.safe_strip(
                stadium_li[0].xpath("span/span/text()").get()
            )
        else:
            attributes['stadium_name'] = None
            attributes['stadium_seats'] = None

        # net transfer record
        attributes['net_transfer_record'] = self.safe_strip(
            response.xpath("//li[contains(text(),'Current transfer record:')]/span/span/a/text()").get()
        )

        # coach name
        coach_name = response.xpath('//div[contains(@data-viewport, "Mitarbeiter")]//div[@class="container-hauptinfo"]/a/text()').get()
        attributes['coach_name'] = coach_name.strip() if coach_name else None

        # code & name from the club's URL
        attributes['code'] = unquote(urlparse(base["href"]).path.split("/")[1])

        # fallback if the main itemprop=legalName doesn't exist
        name_selector = response.xpath("//span[@itemprop='legalName']/text()") \
                        or response.xpath('//h1[contains(@class,"data-header__headline-wrapper")]/text()')
        attributes['name'] = self.safe_strip(name_selector.get())

        # clean whitespace
        for k, v in attributes.items():
            if isinstance(v, str):
                attributes[k] = v.strip()

        yield {
            **base,  # merges in competition_code, competition_type, etc.
            **attributes
        }
