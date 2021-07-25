from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response # required for debugging
import re
from inflection import parameterize, underscore

class PlayersSpider(BaseSpider):
  name = 'players'

  def parse(self, response, parent):
      """Parse clubs's page to collect all player's urls.

        @url https://www.transfermarkt.co.uk/manchester-city/kader/verein/281/saison_id/2019
        @returns requests 34 34
        @cb_kwargs {"parent": "dummy"}
      """

      player_hrefs = response.css(
            'a.spielprofil_tooltip::attr(href)'
        ).getall()

      without_duplicates = list(set(player_hrefs))

      for href in without_duplicates:
          
          cb_kwargs = {
            'base' : {
              'type': 'player',
              'href': href,
              'parent': parent
            }
          }

          yield response.follow(href, self.parse_details, cb_kwargs=cb_kwargs)

  def parse_details(self, response, base):
    """Extract player details from the main page.
    It currently only parses the PLAYER DATA section.

      @url https://www.transfermarkt.co.uk/joel-mumbongo/profil/spieler/381156
      @returns items 1 1
      @cb_kwargs {"base": {"href": "some_href", "type": "player", "parent": {}}}
      @scrapes href type parent
    """
    # parse 'PLAYER DATA' section
    attributes_table = response.css('table.auflistung tr')
    attributes = {}
    for row in attributes_table:
      key = parameterize(row.xpath('th/text()').get().strip(), separator='_')

      # try extracting the value as text
      value = row.xpath('td//text()').get()
      if not value or len(value.strip()) == 0:
        # if text extraction fails, attempt 'href' extraction
        href = row.xpath('td//a/@href').get()
        if href and len(href.strip()) > 0:
          value = {
            'href': row.xpath('td//a/@href').get()
          }
        # if both text and href extraction fails, it must be text + image kind of cell
        # "approximate" parsing extracting the 'title' property
        else:
          text = row.xpath('td//img/@title').get()
          value = text
      else:
        value = value.strip()
      attributes[key] = value

    yield {
      **base,
      **attributes
    }
