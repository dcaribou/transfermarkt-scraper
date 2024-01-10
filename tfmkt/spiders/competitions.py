from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response # required for debugging
import re
import json

from inflection import parameterize, underscore

class CompetitionsSpider(BaseSpider):

  name = 'competitions'

  international_competitions = {}

  def parse(self, response, parent):
    """Parse confederations page. From this page we collect all
    confederation's competitions urls

    @url https://www.transfermarkt.co.uk/wettbewerbe/europa
    @returns requests 25 25
    @cb_kwargs {"parent": {}}
    """
    # uncommenting the two lines below will open a scrapy shell with the context of this request
    # when you run the crawler. this is useful for developing new extractors

    # inspect_response(response, self)
    # exit(1)

    table_rows = response.css('table.items tbody tr.odd, table.items tbody tr.even')

    for row in table_rows[0:]:
      country_image_url = row.xpath('td')[1].css('img::attr(src)').get()
      country_name = row.xpath('td')[1].css('img::attr(title)').get()
      country_code = (
          row
            .xpath('td')[0]
            .xpath('table/tr/td')[1]
            .xpath('a/@href').get()
            .split('/')[-1]
        )

      total_clubs = row.css('td:nth-of-type(3)::text').get()
      total_players = row.css('td:nth-of-type(4)::text').get()
      average_age = row.css('td:nth-of-type(5)::text').get()
      foreigner_percentage = row.css('td:nth-of-type(6) a::text').get()

      total_value = row.css('td:nth-of-type(8)::text').get()

      matches = re.search('([0-9]+)\.png', country_image_url, re.IGNORECASE)
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
    """Parse competitions from the country competitions page.

    @url https://www.transfermarkt.co.uk/wettbewerbe/national/wettbewerbe/157
    @returns items 3 3
    @cb_kwargs {"base": {"href": "some_href/3", "type": "competition", "parent": {}, "country_id": 1, "country_name": "n", "country_code": "CC"}}
    @scrapes type href parent country_id country_name country_code competition_type
    """

    # uncommenting the two lines below will open a scrapy shell with the context of this request
    # when you run the crawler. this is useful for developing new extractors

    # inspect_response(response, self)
    # exit(1)

    competitions = {}
    domestic_competitions_tag = 'Domestic leagues & cups'
    parameterized_domestic_competitions_tag = (
      underscore(parameterize(domestic_competitions_tag))
    )
    international_competitions_tag = 'International competitions'
    parameterized_international_competitions_tag = (
      underscore(parameterize(international_competitions_tag))
    )

    boxes = response.css('div.box')

    relevant_boxes = {}

    for box in boxes:
      box_header = self.safe_strip(box.css('h2.content-box-headline::text').get())
      if box_header in [
          domestic_competitions_tag,
          international_competitions_tag
        ]:
        relevant_boxes[box_header] = box

    # parse domestic competitions

    box = relevant_boxes[domestic_competitions_tag]
    box_body = box.xpath('div[@class="responsive-table"]//tbody')[0]
    box_rows = box_body.xpath('tr')

    competitions[parameterized_domestic_competitions_tag] = []

    for idx, row in enumerate(box_rows):
      tier = row.xpath('td/text()').get()
      if tier in [
        'First Tier',
        'Domestic Cup',
        'Domestic Super Cup'
      ]:
        parameterized_tier = underscore(parameterize(tier))
        competition_row = box_rows[idx + 1]
        competition_href = competition_row.xpath('td/table//td')[1].xpath('a/@href').get()
        competitions[parameterized_domestic_competitions_tag].append(
          {
            'type': 'competition',
            'competition_type': parameterized_tier,
            'href':competition_href
          }
        )

    # parse international competitions

    self.international_competitions['parent'] = base['parent']

    if international_competitions_tag in relevant_boxes.keys():
      box = relevant_boxes[international_competitions_tag]
      box_rows = box.xpath('div[@class = "responsive-table"]//tr[contains(@class, "bg_blau_20")]')

      for row in box_rows:
        competition_href = row.xpath('td')[1].xpath('a/@href').get()
        competition_href_wo_season = re.sub(r'/saison_id/[0-9]{4}','', competition_href)
        tier = row.xpath('td')[1].xpath('a/text()').get()

        parameterized_tier = underscore(parameterize(tier))

        # international competitions are saved to the dynamic dict 'international_competitions' rather than "yielded"
        # this is to avoid emitting duplicated items for international competitions, since the same competitions
        # appear in multiple country pages 
        self.international_competitions[parameterized_tier] = {
          'type': 'competition',
          'href': competition_href_wo_season,
          'competition_type': parameterized_tier
        }

    for competition in competitions[parameterized_domestic_competitions_tag]:
      yield {
        'type': 'competition',
        **base,
        **competition
      }

  def closed(self, reason):

    for key in self.international_competitions.keys():

      if key == 'parent':
        continue

      competition = {
        'type': 'competition',
        'parent': self.international_competitions['parent'],
        **self.international_competitions[key]
      }

      print(json.dumps(competition)) # TODO: this needs to be yielded too!
