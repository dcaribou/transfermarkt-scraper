from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response # required for debugging
import re

from inflection import parameterize, underscore

class CompetitionsSpider(BaseSpider):
  name = 'competitions'

  def parse(self, response, parent):
    """Parse confederations page. From this page we collect all
    confederation's leagues urls

    @url https://www.transfermarkt.co.uk/wettbewerbe/europa
    @returns requests 25 25
    @cb_kwargs {"parent": {}}
    """
    # uncommenting the two lines below will open a scrapy shell with the context of this request
    # when you run the crawler. this is useful for developing new extractors

    # inspect_response(response, self)
    # exit(1)

    table_rows = response.css('table.items tbody').xpath('tr')

    for row in table_rows[1:]:
      country_image_url = row.xpath('td')[1].css('img::attr(src)').get()
      country_name = row.xpath('td')[1].css('img::attr(title)').get()
      country_code = (
          row
            .xpath('td')[0]
            .xpath('table/tr/td')[1]
            .xpath('a/@href').get()
            .split('/')[-1]
        )

      matches = re.search('([0-9]+)\.png', country_image_url, re.IGNORECASE)
      country_id = matches.group(1)

      href = "/wettbewerbe/national/wettbewerbe/" + country_id

      cb_kwargs = {
        'base': {
          'parent': parent,
          'country_id': country_id,
          'country_name': country_name,
          'country_code': country_code
        }
      }

      yield response.follow(self.base_url + href, self.parse_competitions, cb_kwargs=cb_kwargs)

  def parse_competitions(self, response, base):
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
      box_header = box.css('div.table-header h2::text').get()
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

    box = relevant_boxes[international_competitions_tag]
    box_rows = box.xpath('div[@class = "responsive-table"]//tr[contains(@class, "bg_blau_20")]')
    competitions[parameterized_international_competitions_tag] = []

    for row in box_rows:
      competition_href = row.xpath('td')[1].xpath('a/@href').get()
      tier = row.xpath('td')[1].xpath('a/text()').get()

      parameterized_tier = underscore(parameterize(tier))

      competitions[parameterized_international_competitions_tag].append(
          {
            'type': 'competition',
            'competition_type': parameterized_tier,
            'href':competition_href
          }
        )


    yield {
      'type': 'competition',
      **base,
      **competitions
    }
