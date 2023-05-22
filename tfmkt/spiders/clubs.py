from tfmkt.spiders.common import BaseSpider
from urllib.parse import unquote, urlparse
import re

from scrapy.shell import inspect_response # required for debugging

class ClubsSpider(BaseSpider):
  name = 'clubs'

  def parse(self, response, parent):
    """Parse competition page. From this page we collect all competition's
    teams urls

    @url https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1
    @returns requests 20 20
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

        cb_kwargs = {
          'base' : {
            'type': 'club',
            'href': href_strip_season,
            'parent': parent
          }
        }

        yield response.follow(href, self.parse_details, cb_kwargs=cb_kwargs)

  def parse_details(self, response, base):
    """Extract club details from the main page.

      @url https://www.transfermarkt.co.uk/fc-bayern-munchen/startseite/verein/27
      @returns items 1 1
      @cb_kwargs {"base": {"href": "some_href/path/to/code", "type": "club", "parent": {}}}
      @scrapes href type parent
    """

    # uncommenting the two lines below will open a scrapy shell with the context of this request
    # when you run the crawler. this is useful for developing new extractors

    # inspect_response(response, self)
    # exit(1)

    attributes = {}

    # parsing of "dataMarktwert" section

    attributes['total_market_value'] = response.css('div.dataMarktwert a::text').get()

    # parsing of "dataContent" section

    attributes['squad_size'] = self.safe_strip(
      response.xpath("//li[contains(text(),'Squad size:')]/span/text()").get()
    )

    attributes['average_age'] = self.safe_strip(
      response.xpath("//li[contains(text(),'Average age:')]/span/text()").get()
    )
    
    foreigners_element = response.xpath("//li[contains(text(),'Foreigners:')]")[0]
    attributes['foreigners_number'] = self.safe_strip(foreigners_element.xpath("span/a/text()").get())
    attributes['foreigners_percentage'] = self.safe_strip(
      foreigners_element.xpath("span/span/text()").get()
    )

    attributes['national_team_players'] = self.safe_strip(
      response.xpath("//li[contains(text(),'National team players:')]/span/a/text()").get()
    )

    stadium_element = response.xpath("//li[contains(text(),'Stadium:')]")[0]
    attributes['stadium_name'] = self.safe_strip(
      stadium_element.xpath("span/a/text()").get()
    )
    attributes['stadium_seats'] = self.safe_strip(
      stadium_element.xpath("span/span/text()").get()
    )

    attributes['net_transfer_record'] = self.safe_strip(
      response.xpath("//li[contains(text(),'Current transfer record:')]/span/span/a/text()").get()
    )

    # parsing of "Coach for the season"
    attributes['coach_name'] = (
      response
        .xpath('//div[contains(@data-viewport, "Mitarbeiter")]//div[@class="container-hauptinfo"]/a/text()')
        .get()
        
    )
    
    
    attributes['code'] = unquote(urlparse(base["href"]).path.split("/")[1])
    attributes['name'] = self.safe_strip(
       response.xpath("//span[@itemprop='legalName']/text()").get()
    ) or self.safe_strip(
       response.xpath('//h1[@class="data-header__headline-wrapper data-header__headline-wrapper--oswald"]/text()').get()
    )

    for key, value in attributes.items():
      if value:
        attributes[key] = value.strip()
      else:
        attributes[key] = value

    yield {
      **base,
      **attributes
    }
