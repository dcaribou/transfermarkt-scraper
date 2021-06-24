import scrapy
from scrapy import Request
from scrapy.shell import inspect_response # required for debugging
from urllib.parse import urlparse
from inflection import parameterize, underscore
import json
import os
import sys
import re

default_base_url = 'https://www.transfermarkt.co.uk'

default_confederation_hrefs = [
  '/wettbewerbe/europa',
  '/wettbewerbe/amerika',
  '/wettbewerbe/afrika',
  '/wettbewerbe/asien'
]

class BaseSpider(scrapy.Spider):
  def __init__(self, base_url=None, parents=None):

    if base_url is not None:
      self.base_url = base_url
    else:
      self.base_url = default_base_url
    
    if parents is not None:
      with open(parents) as json_file:
        lines = json_file.readlines()
        parents = [ json.loads(line) for line in lines ]
    elif not sys.stdin.isatty():
        parents = [ json.loads(line) for line in sys.stdin ]
    else:
      parents = self.scrape_parents()

    # 2nd level parents are redundat
    for parent in parents:
      if parent.get('parent') is not None:
        del parent['parent']

    self.entrypoints = parents

  def scrape_parents(self):
    if not os.environ.get('SCRAPY_CHECK'):
      raise Exception("Backfilling is not yet supported, please provide a 'parents' file")
    else:
      return []

  def start_requests(self):
    
    season = self.settings['SEASON']

    for item in self.entrypoints:
      if item['type'] in ['club']:
        item['seasoned_href'] = f"{self.base_url}{item['href']}/saison_id/{season}"
      elif item['type'] in ['league']:
        item['seasoned_href'] = f"{self.base_url}{item['href']}/plus/0?saison_id={season}"
      else:
        item['seasoned_href'] = f"{self.base_url}{item['href']}"

    return [
      Request(
        item['seasoned_href'],
        cb_kwargs={
          'parent': item
        }
      )
      for item in self.entrypoints
    ]
 

class ConfederationsSpider(BaseSpider):
    name = 'confederations'

    def scrape_parents(self):
      return [ {'type': 'root', 'href': ""} ]

    def parse(self, response, **kwargs):
      for href in default_confederation_hrefs:
        yield {'type': 'confederation', 'href': href}

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

class ClubsSpider(BaseSpider):
  name = 'clubs'

  def parse(self, response, parent):
    """Parse competition page. From this page we collect all competition's
    teams urls

    @url https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1
    @returns items 20 20
    @cb_kwargs {"parent": "dummy"}
    @scrapes type href parent
    """

    def is_teams_table(table):
        """Checks whether a table is expected to contain teams information
        or not, by looking for the word 'Club' in the table headers.
        """
        return True if table.css('th::text')[0].get().lower() == 'club' else False

    def extract_team_href(row):
        """It extracts one team's href from a teams' table row"""
        return row.css('td')[1].css('a::attr(href)').get()

    # get all 'responsive-tabes' in the page
    page_tables = response.css(
        'div.responsive-table'
    )
    with_teams_info = [
        table for table in page_tables if is_teams_table(table)
    ]
    assert(len(with_teams_info) == 1)
    for row in with_teams_info[0].css('tbody tr'):
        href = extract_team_href(row)
        href_strip_season = re.sub('/saison_id/[0-9]{4}$', '', href)

        # follow urls
        yield {
          'type': 'club', 'href': href_strip_season, 'parent': parent
        }

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

class AppearancesSpider(BaseSpider):
  name = 'appearances'

  def parse(self, response, parent):
    """Parse player profile attributes and fetch "full stats" URL

    @url https://www.transfermarkt.co.uk/sergio-aguero/profil/spieler/26399
    @returns requests 1 1
    @cb_kwargs {"parent": "dummy"}
    """

    season = self.settings['SEASON']

    full_stats_href = response.xpath('//a[contains(text(),"View full stats")]/@href').get()
    seasoned_full_stats_href = full_stats_href + f"/plus/0?saison={season}"

    yield response.follow(seasoned_full_stats_href, self.parse_stats, cb_kwargs={'parent': parent})

  def parse_stats(self, response, parent):
    """Parse player's full stats. From this page we collect all player appearances

    @url https://www.transfermarkt.co.uk/sergio-aguero/leistungsdaten/spieler/26399
    @returns items 9
    @cb_kwargs {"parent": "dummy"}
    @scrapes assists competition_code date for goals href matchday minutes_played opponent parent pos red_cards result second_yellow_cards type venue yellow_cards
    """

    def parse_stats_table(table):
        """Parses a table of player's statistics."""
        header_elements = [
            underscore(parameterize(header)) for header in
            table.css("th::text").getall() + table.css(
                "th > span::attr(title)"
            ).getall()
        ]
        # for some reason, sometimes transfermarket might call the matchday as spieltag
        # here we make sure that if that's the case we revert it back to matchday
        header_elements = [header if header != 'spieltag' else 'matchday' for header in header_elements]

        value_elements_matrix = [
          [ parse_stats_elem(element) for element in row.xpath('td') if parse_stats_elem(element) is not None
          ] for row in table.css('tr') if len(row.css('td').getall()) > 9 # TODO: find a way to include 'on the bench' and 'not in squad' occurrences
        ]

        for value_elements in value_elements_matrix:
          header_elements_len = len(header_elements)
          value_elements_len = len(value_elements)
          assert(header_elements_len == value_elements_len), f"Header ({header_elements_len}) - cell element ({value_elements_len}) mismatch at {response.url}"
          yield dict(zip(header_elements, value_elements))

    def parse_stats_elem(elem):
        """Parse an individual table cell"""
        # some cells include the club classification in the national league in brackets. for example, "Leeds (10.)"
        # these are at the same time unncessary and annoying to parse, as club information can be obtained
        # from the "shield" image. identify these cells by looking for descendents of the class 'tabellenplatz'
        has_classification_in_brackets = elem.xpath('*[@class = "tabellenplatz"]').get() is not None
        # club information is parsed from team "shields" using a separate logic from the rest
        # identify cells containing club shields
        has_shield_class = elem.css('img.tiny_wappen').get() is not None
        club_href = elem.css('a.vereinprofil_tooltip::attr(href)').get()
        result_href = elem.css('a.ergebnis-link::attr(href)').get()

        if (
            (has_classification_in_brackets and club_href is None) or
            (club_href is not None and not has_shield_class) 
            ):
          return None
        elif club_href is not None:
          return {'type': 'club', 'href': club_href}
        elif result_href is not None:
          return {'type': 'game', 'href': result_href}
        # finally, most columns can be parsed by extracting the text at the element's "last leaf"
        else:
          return elem.xpath('string(.)').get().strip()

    # stats tables are 'responsive-tables' (except the first one, which is
    # a summary table)
    competitions = response.css(
        'div.table-header > a::attr(name)'
    ).getall()[1:]
    stats_tables = response.css('div.responsive-table')[1:]
    assert(len(competitions) == len(stats_tables))
    all_stats = {}
    for competition_name, table in zip(competitions, stats_tables):
      stats = list(parse_stats_table(table))
      all_stats[competition_name] = stats

    url = urlparse(response.url).path
    for competition_name, appearances in all_stats.items():
      for appearance in appearances:
        yield {
          'type': 'appearance',
          'href': url,
          'parent': parent,
          'competition_code': competition_name,
          **appearance
        }
