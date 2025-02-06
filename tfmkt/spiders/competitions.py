from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response  # for debugging
import re
import json
from inflection import parameterize, underscore

class CompetitionsSpider(BaseSpider):
    name = 'competitions'

    def parse(self, response, parent):
        """
        Parse confederations page. From this page we collect all
        confederation's competitions urls, then go to their national
        competition pages.

        @url https://www.transfermarkt.co.uk/wettbewerbe/europa
        @returns requests
        @cb_kwargs {"parent": {}}
        """
        table_rows = response.css('table.items tbody tr.odd, table.items tbody tr.even')

        for row in table_rows:
            country_image_url = row.xpath('td')[1].css('img::attr(src)').get()
            country_name = row.xpath('td')[1].css('img::attr(title)').get()
            country_code = (
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

            href = "/wettbewerbe/national/wettbewerbe/" + country_id

            cb_kwargs = {
                'base': {
                    'parent': parent,
                    'country_id': country_id,
                    'country_name': country_name,
                    'country_code': country_code,
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
        Parse competitions from a specific country's page, capturing
        all league tiers but excluding cups, super cups, and ignoring
        international competitions.

        @url https://www.transfermarkt.co.uk/wettbewerbe/national/wettbewerbe/157
        @returns items
        @cb_kwargs {"base": {"country_id": 1, ...}}
        @scrapes type href parent country_id country_name country_code competition_type
        """
        domestic_competitions_tag = 'Domestic leagues & cups'
        boxes = response.css('div.box')
        relevant_box = None

        # Locate the box with the header "Domestic leagues & cups"
        for box in boxes:
            box_header = self.safe_strip(box.css('h2.content-box-headline::text').get())
            if box_header == domestic_competitions_tag:
                relevant_box = box
                break

        if not relevant_box:
            return  # no domestic box found

        # table with tiers & comps
        box_body = relevant_box.xpath('div[@class="responsive-table"]//tbody')[0]
        box_rows = box_body.xpath('tr')

        # Each "tier" row is typically followed by a row with the actual link.
        idx = 0
        while idx < len(box_rows):
            tier_row = box_rows[idx]
            tier_name = tier_row.xpath('td/text()').get() or ""

            # Exclude "Domestic Cup" and "Domestic Super Cup"
            if tier_name not in ("Domestic Cup", "Domestic Super Cup"):
                # Next row often has the link
                link_row_idx = idx + 1
                if link_row_idx < len(box_rows):
                    link_row = box_rows[link_row_idx]
                    competition_href = link_row.xpath('td/table//td')[1].xpath('a/@href').get()
                    if competition_href:
                        parameterized_tier = underscore(parameterize(tier_name))
                        yield {
                            'type': 'competition',
                            **base,
                            'competition_type': parameterized_tier,
                            'href': competition_href
                        }
                # else: no next row, so no link
            # move to the next pair
            idx += 2

    def closed(self, reason):
        """
        We won't yield international competitions (nor cups).
        So, no logic needed here if skipping them entirely.
        """
        pass
