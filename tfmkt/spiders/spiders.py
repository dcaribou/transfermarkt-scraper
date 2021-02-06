import scrapy
from scrapy import Request
from scrapy.shell import inspect_response # required for debugging
from inflection import parameterize, underscore
import json

default_base_url = 'https://www.transfermarkt.co.uk'

default_confederation_hrefs = [
  '/wettbewerbe/europa',
  '/wettbewerbe/amerika',
  '/wettbewerbe/afrika',
  '/wettbewerbe/asien'
]

class BaseSpider(scrapy.Spider):
  def __init__(self, base_url=None):

    # set argument defaults
    if base_url is not None:
      self.base_url = base_url
    else:
      self.base_url = default_base_url

  def start_requests(self):
    return [
      Request(
        f"{self.base_url}{item['href']}",
        cb_kwargs={
          'parent': item
        }
      )
      for item in self.entrypoints
    ]
 

class ConfederationsSpider(BaseSpider):
    name = 'confederations'

    def __init__(self, base_url=None):
        self.entrypoints = [ {'type': 'root', 'href': ""} ]
        super().__init__(base_url)

    def parse(self, response, **kwargs):
      for href in default_confederation_hrefs:
        yield {'type': 'confederation', 'href': href}

class LeaguesSpider(BaseSpider):
  name = 'leagues'

  def __init__(self, base_url=None, confederations=None):

      # set argument defaults

      if confederations is not None:
        with open(confederations) as json_file:
          lines = json_file.readlines()
          hrefs = [ json.loads(line)['href'] for line in lines  ]
      else:
        hrefs = default_confederation_hrefs

      self.entrypoints = [
        {'type': 'confederation', 'href': href}
        for href in hrefs
      ]

      super().__init__(base_url)

  def parse(self, response, parent):
    """Parse confederations page. From this page we collect all
    confederation's leagues urls

    @url https://www.transfermarkt.co.uk/wettbewerbe/europa
    @returns requests 25 25
    @scrapes competition
    """
    # competitions entries in the confederation page
    leagues_query = response.css(
        'table.items tbody tr:first-child a[title]::attr(href)'
    )
    for match in leagues_query:
      url = match.getall()[0]
      yield {'type': 'league', 'href': url, 'parent': parent}

class ClubsSpider(BaseSpider):
  name = 'clubs'

  def __init__(self, base_url=None, confederations=None, leagues=None):

      # set argument defaults

      if leagues is not None:
        with open(leagues) as json_file:
          lines = json_file.readlines()
          hrefs = [ json.loads(line)['href'] for line in lines  ]
      else:
        hrefs = self.scrape_leagues(base_url, confederations)['href']

      self.entrypoints = [
        {'type': 'league', 'href': href}
        for href in hrefs
      ]

      super().__init__(base_url)

  def scrape_leagues(self, base_url, confederations):
    # ideally we would crawl 'leagues' at this point and pass the results to the clubs
    # spider to continue, however this is not yet implemented
    raise Exception("League URLs backfilling is not yet supported, please provide a 'leagues' file")


  def parse(self, response, parent):
    """Parse competition page. From this page we collect all competition's
    teams urls

    @url https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1
    @returns requests 20 20
    @scrapes team
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

        # follow urls
        yield {
          'type': 'club', 'href': href, 'parent': parent
        }

class PlayersSpider(BaseSpider):
  name = 'players'

  def __init__(self, base_url=None, leagues=None, clubs=None):

      # set argument defaults

      if clubs is not None:
        with open(clubs) as json_file:
          lines = json_file.readlines()
          hrefs = [ json.loads(line)['href'] for line in lines  ]
      else:
        hrefs = self.scrape_clubs(base_url, leagues)['href']

      self.entrypoints = [
        {'type': 'club', 'href': href}
        for href in hrefs
      ]

      super().__init__(base_url)


  def scrape_clubs(self, base_url, leagues):
    # ideally we would crawl 'leagues' at this point and pass the results to the clubs
    # spider to continue, however this is not yet implemented
    raise Exception("Club URLs backfilling is not yet supported, please provide a 'clubs' file")


  def parse(self, response, parent):
      """Parse clubs's page to collect all player's urls.

        @url https://www.transfermarkt.co.uk/manchester-city/kader/verein/281/saison_id/2019
        @returns requests 34 34
        @scrapes player
      """

      player_hrefs = response.css(
            'a.spielprofil_tooltip::attr(href)'
        ).getall()

      without_duplicates = list(set(player_hrefs))

      for href in without_duplicates:
          yield {
            'type': 'player',
            'href': href,
            'parent': parent
          }

class AppearancesSpider(BaseSpider):
  name = 'appearances'

  def __init__(self, base_url=None, players=None):

    # set argument defaults

    if players is not None:
      with open(players) as json_file:
        lines = json_file.readlines()
        hrefs = [ json.loads(line)['href'] for line in lines  ]
    else:
      hrefs = self.scrape_players(base_url, players)['href']

    self.entrypoints = [
      {'type': 'player', 'href': href}
      for href in hrefs
    ]

    super().__init__(base_url)

  def parse(self, response, parent):
    full_stats_href = response.xpath('//a[contains(text(),"View full stats")]/@href').get()
    yield response.follow(full_stats_href + '/plus/1', self.parse_stats, cb_kwargs={'parent': parent})

  def parse_stats(self, response, parent):
      
    def parse_stats_table(table):
        """Parses a table of player's statistics."""
        header_elements = [
            underscore(parameterize(header)) for header in
            table.css("th::text").getall() + table.css(
                "th > span::attr(title)"
            ).getall()
        ]

        value_elements_matrix = [
            [
                parse_stats_elem(element).strip() for element in row.xpath(
                    'td[not(descendant::*[local-name() = "img"])]'
                )
            ]
            for row in table.css('tr') if len(row.css('td').getall()) > 8
        ]

        for value_elements in value_elements_matrix:
            assert(len(header_elements) == len(value_elements))
            yield dict(zip(header_elements, value_elements))

    def parse_stats_elem(elem):
        """Parse an individual table cell"""

        team = elem.css('a.vereinprofil_tooltip::attr(href)').get()
        if team is not None:
            return team.split('/')[1]
        else:
            return elem.xpath('string(.)').get()

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
    yield {
      'stats': all_stats,
      'parent': parent
    }
