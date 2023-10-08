from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response # required for debugging
import re
from tfmkt.utils import background_position_in_px_to_minute

class GameLineupsSpider(BaseSpider):
  name = 'game_lineups'

  def parse(self, response, parent):
    """Parse game page.

    @url https://www.transfermarkt.co.uk/spielbericht/index/spielbericht/3098550
    @returns requests 1 1
    @cb_kwargs {"parent": {"href": "some_href", "home_club": {"href": "some_href"}, "away_club": {"href": "some_href"}}}
    @scrapes type href parent
    """

    # uncommenting the two lines below will open a scrapy shell with the context of this request
    # when you run the crawler. this is useful for developing new extractors

    # inspect_response(response, self)
    # exit(1)

    lineups_url = parent['href'].replace('index', 'aufstellung')
    lineups_elements = response.xpath(
      f".//div[./h2/@class = 'content-box-headline' and normalize-space(./h2/text()) = 'Line-Ups']/div[contains(@class, 'columns')]"
    )
    home_linup = lineups_elements[0]
    away_linup = lineups_elements[1]

    home_formation = self.safe_strip(home_linup.xpath("./div[@class = 'row']/div/text()").get())
    away_formation = self.safe_strip(away_linup.xpath("./div[@class = 'row']/div/text()").get())

    lineups = {
      'home_club': {
        'href': parent['home_club']['href'],
        'formation': home_formation,
        'starting_lineup': [],
        'substitutes': []
      },
      'away_club': {
        'href': parent['away_club']['href'],
        'formation': away_formation,
        'starting_lineup': [],
        'substitutes': []
      }
    }
    
    cb_kwargs = {
      'base': {
        'parent': parent,
        'lineups': lineups,
        'href': lineups_url
      }
    }
      
    return response.follow(lineups_url, self.parse_lineups, cb_kwargs=cb_kwargs)

  def parse_lineups(self, response, base):
    """Parse lineups.

    @url https://www.transfermarkt.co.uk/spielbericht/aufstellung/spielbericht/3098550
    @returns items 1 1
    @cb_kwargs {"base": {"href": "some_href", "lineups": {"home_club": {"formation": "Starting Line-up: 4-3-3", "starting_lineup": [], "substitutes": []}, "away_club": {"formation": "Starting Line-up: 4-3-3", "starting_lineup": [], "substitutes": []}}, "parent": {"href": "some_href", "type": "game", "game_id": 123}}}
    @scrapes type parent game_id href home_club away_club
    """

    parent = base['parent']
    lineups = base['lineups']

    starting_elements = response.xpath(
      f"//div[./h2[contains(@class, 'content-box-headline')] and normalize-space(./h2/text()) = 'Starting Line-up']//div[@class='responsive-table']"
    )
    substitutes_elements = response.xpath(
      f"//div[./h2[contains(@class, 'content-box-headline')] and normalize-space(./h2/text()) = 'Substitutes']//div[@class='responsive-table']"
    )

    for i in range(len(starting_elements)):
      tr_elements = starting_elements[i].xpath("./table[@class = 'items']//tr")
      defenders_count = 0
      midfielders_count = 0
      forwards_count = 0
      for j in range(len(tr_elements)):
        e = tr_elements[j]
        idx = j % 3
        number_idx = idx == 0
        player_idx = idx == 1
        position_idx = idx == 2
        if number_idx:
          player = {}
          player['number'] = e.xpath("./td/div[@class = 'rn_nummer']/text()").get()
        elif player_idx:
          player['href'] = e.xpath("./td/a/@href").get()
          player['name'] = e.xpath("./td/a/@title").get()
          player['team_captain'] = 1 if e.xpath("./td/span/@title").get() else 0
        elif position_idx:
          position = self.safe_strip(e.xpath("./td/text()").get().split(',')[0])
          player['position'] = position
          if "Back" in position or "Defender" in position or "defender" in position:
            defenders_count = defenders_count + 1
          elif "Midfield" in position or "midfield" in position:
            midfielders_count = midfielders_count + 1
          elif "Winger" in position or "Forward" in position or "Striker" in position or "Attack" in position:
            forwards_count = forwards_count + 1

        if position_idx:
          if i == 0:
            lineups['home_club']['starting_lineup'].append(player)
          else:
            lineups['away_club']['starting_lineup'].append(player)

      formation = f"{defenders_count}-{midfielders_count}-{forwards_count}" if (defenders_count + midfielders_count + forwards_count) == 10 else None
      if i == 0:
        if lineups['home_club']['formation'] is None:
          lineups['home_club']['formation'] = formation
        else:
          lineups['home_club']['formation'] = lineups['home_club']['formation'].split(':')[1].strip()
      else:
        if lineups['away_club']['formation'] is None:
          lineups['away_club']['formation'] = formation
        else:
          lineups['away_club']['formation'] = lineups['away_club']['formation'].split(':')[1].strip()
      

    for i in range(len(substitutes_elements)):
      tr_elements = substitutes_elements[i].xpath("./table[@class = 'items']//tr")
      for j in range(len(tr_elements)):
        e = tr_elements[j]
        idx = j % 3
        number_idx = idx == 0
        player_idx = idx == 1
        position_idx = idx == 2
        if number_idx:
          player = {}
          player['number'] = e.xpath("./td/div[@class = 'rn_nummer']/text()").get()
        elif player_idx:
          player['href'] = e.xpath("./td/a/@href").get()
          player['name'] = e.xpath("./td/a/@title").get()
          player['team_captain'] = 1 if e.xpath("./td/span/@title").get() else 0
        elif position_idx:
          player['position'] = self.safe_strip(e.xpath("./td/text()").get().split(',')[0])

        if position_idx:
          if i == 0:
            lineups['home_club']['substitutes'].append(player)
          else:
            lineups['away_club']['substitutes'].append(player)

    item = {
      'type': 'game_lineups',
      'parent': {
        'href': parent['href'],
        'type': parent['type'],
      },
      'href': base['href'],
      'game_id': parent['game_id'],
      'home_club': lineups['home_club'],
      'away_club': lineups['away_club']
    }

    yield item
