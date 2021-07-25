from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response # required for debugging
import re

class LeaguesSpider(BaseSpider):
  name = 'leagues'

  def parse(self, response, parent):
    """Parse confederations page. From this page we collect all
    confederation's leagues urls

    @url https://www.transfermarkt.co.uk/wettbewerbe/europa
    @returns items 25 25
    @cb_kwargs {"parent": "dummy"}
    @scrapes type href parent
    """
    # league entries in the confederation page
    leagues_query = response.css(
        'table.items tbody tr:first-child a[title]::attr(href)'
    )
    for match in leagues_query:
      url = match.getall()[0]
      yield {'type': 'league', 'href': url, 'parent': parent}
