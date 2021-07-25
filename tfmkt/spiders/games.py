from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response # required for debugging
import re

class GamesSpider(BaseSpider):
  name = 'games'

  def parse(self, response, parent):
    """Parse leagues page. From this page follow to the games and fixutres page.

    @url https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1
    @returns requests 1 1
    @cb_kwargs {"parent": "dummy"}
    @scrapes type href parent
    """

    footer_links = response.css('div.footer-links')
    for footer_link in footer_links:
      text = footer_link.xpath('a//text()').get()
      if text == "All fixtures & results":
        next_url = footer_link.xpath('a/@href').get()

        cb_kwargs = {
            'base' : {
              'parent': parent
            }
          }

        return response.follow(next_url, self.extract_game_urls, cb_kwargs=cb_kwargs)

  def extract_game_urls(self, response, base):
    """Parse games and fixutres page. From this page follow to each game page.

    @url https://www.transfermarkt.co.uk/premier-league/gesamtspielplan/wettbewerb/GB1/saison_id/2020
    @returns requests 330 390
    @cb_kwargs {"base": {"href": "some_href", "type": "league", "parent": {}}}
    @scrapes type href parent game_id 
    """

    game_links = response.css('a.ergebnis-link')
    for game_link in game_links:
      href = game_link.xpath('@href').get()

      cb_kwargs = {
        'base': {
          'parent': base['parent'],
          'href': href
        }
      }

      yield response.follow(href, self.parse_game, cb_kwargs=cb_kwargs)

  def parse_game(self, response, base):
    """Parse games and fixutres page. From this page follow to each game page.

    @url https://www.transfermarkt.co.uk/caykur-rizespor_fenerbahce-sk/index/spielbericht/3426662
    @returns items 1 1
    @cb_kwargs {"base": {"href": "some_href/3", "type": "league", "parent": {}}}
    @scrapes type href parent game_id result matchday date
    """

    result = response.css('div.sb-endstand::text').get().strip()
    date_attributes = response.css('p.sb-datum').xpath('a/text()')
    matchday = date_attributes[0].get().strip()
    date = date_attributes[1].get().strip()
    game_id = int(base['href'].split('/')[-1])

    home_club_href = response.css('div.sb-heim a::attr(href)').get()
    away_club_href = response.css('div.sb-gast a::attr(href)').get()

    item = {
      **base,
      'type': 'game',
      'game_id': game_id,
      'home_club': {
        'type': 'club',
        'href': home_club_href
      },
      'away_club': {
        'type': 'club',
        'href': away_club_href
      },
      'result': result,
      'matchday': matchday,
      'date': date
    }
    
    yield item
 