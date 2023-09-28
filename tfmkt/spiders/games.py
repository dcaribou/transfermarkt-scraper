from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response # required for debugging
import re
from tfmkt.utils import background_position_in_px_to_minute

class GamesSpider(BaseSpider):
  name = 'games'

  def parse(self, response, parent):
    """Parse competition page. From this page follow to the games and fixutres page.

    @url https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1
    @returns requests 1 1
    @cb_kwargs {"parent": "dummy"}
    @scrapes type href parent
    """

    # uncommenting the two lines below will open a scrapy shell with the context of this request
    # when you run the crawler. this is useful for developing new extractors

    # inspect_response(response, self)
    # exit(1)

    cb_kwargs = {
      'base' : {
        'parent': parent
      }
    }

    footer_links = response.css('div.footer-links')
    for footer_link in footer_links:
      text = footer_link.xpath('a//text()').get().strip()
      if text in [
        "All fixtures & results",
        "All games"
        ]:
        next_url = footer_link.xpath('a/@href').get()

        return response.follow(next_url, self.extract_game_urls, cb_kwargs=cb_kwargs)

  def extract_game_urls(self, response, base):
    """Parse games and fixutres page. From this page follow to each game page.

    @url https://www.transfermarkt.co.uk/premier-league/gesamtspielplan/wettbewerb/GB1/saison_id/2020
    @returns requests 330 390
    @cb_kwargs {"base": {"href": "some_href", "type": "league", "parent": {}}}
    @scrapes type href parent game_id 
    """

    # inspect_response(response, self)
    # exit(1)

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


  def extract_game_events(self, response, event_type):
    event_elements = response.xpath(
      f"//div[./h2/@class = 'content-box-headline' and normalize-space(./h2/text()) = '{event_type}']//div[@class='sb-aktion']"
    )

    events = []
    for e in event_elements:
      event = {}
      event["type"] = event_type
      background_position_match = re.match(
        "background-position: ([-+]?[0-9]+)px ([-+]?[0-9]+)px;",
        e.xpath("./div[1]/span[@class='sb-sprite-uhr-klein']/@style").get()
      )
      event["minute"] = background_position_in_px_to_minute(
        int(background_position_match.group(1)),
        int(background_position_match.group(2)),
      )
      extra_minute_text = self.safe_strip(
        e.xpath("./div[1]/span[@class='sb-sprite-uhr-klein']/text()").get()
      )
      if len(extra_minute_text) <= 1:
        extra_minute = None
      else:
        extra_minute = int(extra_minute_text)

      event["extra"] = extra_minute
      event["player"] = {
        "href": e.xpath("./div[@class = 'sb-aktion-spielerbild']/a/@href").get()
      }
      event["club"] = {
        "name": e.xpath("./div[@class = 'sb-aktion-wappen']/a/@title").get(),
        "href": e.xpath("./div[@class = 'sb-aktion-wappen']/a/@href").get()
      }

      action_element = e.xpath("./div[@class = 'sb-aktion-aktion']")
      event["action"] = {
        "result": self.safe_strip(
          e.xpath("./div[@class = 'sb-aktion-spielstand']/b/text()").get()
        ),
        "description": self.safe_strip(
          # goal/card or substitution description
          (" ".join([s.strip() for s in action_element.xpath("./text()").getall()])).strip() 
            or (" ".join(action_element.xpath(".//span[@class = 'sb-aktion-wechsel-aus']/span/text()").getall())).strip()
        ),
        "player_in": {
          "href": action_element.xpath(".//div/a/@href").get()
        },
        "player_assist": {
          "href": action_element.xpath("./a/@href").getall()[1] if len(action_element.xpath("./a/@href").getall()) > 1 else None
        }
      }
      events.append(event)

    return events

  def parse_lineups(self, response, base):
    """Parse lineups.

    @url https://www.transfermarkt.co.uk/spielbericht/aufstellung/spielbericht/3098550
    @returns items 1 1
    @cb_kwargs {"base": {"item": "game info"}}
    @scrapes starting lineup substitutes
    """

    item = base['item']
    lineups = item['lineups']

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
          if "Back" in position:
            defenders_count = defenders_count + 1
          elif "Midfield" in position:
            midfielders_count = midfielders_count + 1
          elif "Winger" in position or "Forward" in position or "Striker" in position:
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

    item['lineups'] = lineups

    yield item

  def parse_game(self, response, base):
    """Parse games and fixutres page. From this page follow to each game page.

    @url https://www.transfermarkt.co.uk/spielbericht/index/spielbericht/3098550
    @returns items 1 1
    @cb_kwargs {"base": {"href": "some_href/3", "type": "league", "parent": {}}}
    @scrapes type href parent game_id result matchday date stadium attendance home_manager away_manager
    """

    # inspect_response(response, self)
    # exit(1)

    game_id = int(base['href'].split('/')[-1])

    game_box = response.css('div.box-content')

    # extract home and away "boxes" attributes
    home_club_box = game_box.css('div.sb-heim')
    away_club_box = game_box.css('div.sb-gast')

    home_club_href = home_club_box.css('a::attr(href)').get()
    away_club_href = away_club_box.css('a::attr(href)').get()

    home_club_position = home_club_box[0].xpath('p/text()').get()
    away_club_position = away_club_box[0].xpath('p/text()').get()

    # extract date and time "box" attributes
    datetime_box = game_box.css('div.sb-spieldaten')[0]

    text_elements = [
      element for element in datetime_box.xpath('p//text()') 
      if len(self.safe_strip(element.get())) > 0
    ]

    matchday = self.safe_strip(text_elements[0].get()).split("  ")[0]
    date = self.safe_strip(datetime_box.xpath('p/a[contains(@href, "datum")]/text()').get())
    
    # extract venue "box" attributes
    venue_box = game_box.css('p.sb-zusatzinfos')

    stadium = self.safe_strip(venue_box.xpath('node()')[1].xpath('a/text()').get())
    attendance = self.safe_strip(venue_box.xpath('node()')[1].xpath('strong/text()').get())
    referee = self.safe_strip(venue_box.xpath('a[contains(@href, "schiedsrichter")]/@title').get())

    # extract results "box" attributes
    result_box = game_box.css('div.ergebnis-wrap')

    result = self.safe_strip(result_box.css('div.sb-endstand::text').get())

    # extract from line-ups "box"
    manager_names = response.xpath(
        "//tr[(contains(td/b/text(),'Manager')) or (contains(td/div/text(),'Manager'))]/td[2]/a/text()"
      ).getall()

    game_events = (
      self.extract_game_events(response, event_type="Goals") +
      self.extract_game_events(response, event_type="Substitutions") +
      self.extract_game_events(response, event_type="Cards")
    )

    item = {
      **base,
      'type': 'game',
      'game_id': game_id,
      'home_club': {
        'type': 'club',
        'href': home_club_href
      },
      'home_club_position': home_club_position,
      'away_club': {
        'type': 'club',
        'href': away_club_href
      },
      'away_club_position': away_club_position,
      'result': result,
      'matchday': matchday,
      'date': date,
      'stadium': stadium,
      'attendance': attendance,
      'referee': referee,
      'events': game_events
    }

    if len(manager_names) == 2:
      home_manager_name, away_manager_name = manager_names
      item["home_manager"] = {
        'name': home_manager_name
      }
      item["away_manager"] = {
        'name': away_manager_name
      }

    lineups_url = base['href'].replace('index', 'aufstellung')
    lineups_elements = response.xpath(
      f".//div[./h2/@class = 'content-box-headline' and normalize-space(./h2/text()) = 'Line-Ups']/div[contains(@class, 'columns')]"
    )
    home_linup = lineups_elements[0]
    away_linup = lineups_elements[1]

    home_formation = self.safe_strip(home_linup.xpath("./div[@class = 'row']/div/text()").get())
    away_formation = self.safe_strip(away_linup.xpath("./div[@class = 'row']/div/text()").get())

    lineups = {
      'href': lineups_url,
      'home_club': {
        'formation': home_formation,
        'starting_lineup': [],
        'substitutes': []
      },
      'away_club': {
        'formation': away_formation,
        'starting_lineup': [],
        'substitutes': []
      }
    }

    item['lineups'] = lineups
    
    cb_kwargs = {
        'base': {
          'item': item
        }
      }
      
    yield response.follow(lineups_url, self.parse_lineups, cb_kwargs=cb_kwargs)
 