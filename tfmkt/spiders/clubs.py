from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response # required for debugging
import re

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
      @cb_kwargs {"base": {"href": "some_href", "type": "club", "parent": {}}}
      @scrapes href type parent
    """

    attributes = {}

    # parsing of "dataMarktwert" section

    attributes['total_market_value'] = response.css('div.dataMarktwert a::text').get()

    # parsing of "dataContent" section

    squad_size_element = response.xpath('//p[span[@class="dataItem"] = "Squad size:"]')[0]
    attributes['squad_size'] = squad_size_element.xpath('span[@class="dataValue"]/text()').get().strip()

    average_age_element = response.xpath('//p[span[@class="dataItem"] = "Average age:"]')[0]
    attributes['average_age'] = average_age_element.xpath('span[@class="dataValue"]/text()').get().strip()

    foreigners_element = response.xpath('//p[span[@class="dataItem"] = " Foreigners:"]')[0]
    attributes['foreigners_number'] = foreigners_element.xpath('span[@class="dataValue"]/a/text()').get().strip()
    attributes['foreigners_percentage'] = foreigners_element.xpath('span[@class="dataValue"]/span/text()').get().strip()

    national_team_players_element = response.xpath('//p[span[@class="dataItem"] = "National team players:"]')[0]
    attributes['national_team_players'] = (
      national_team_players_element
        .xpath('span[@class="dataValue"]/a/text()')
        .get()
        .strip()
    )

    stadium_element = response.xpath('//p[span[@class="dataItem"] = "Stadium:"]')[0]
    attributes['stadium_name'] = stadium_element.xpath('span[@class="dataValue"]/a/text()').get().strip()
    attributes['stadium_seats'] = stadium_element.xpath('span[@class="dataValue"]/span/text()').get().strip()

    transfer_record_element = response.xpath('//p[span[@class="dataItem"] = "Current transfer record:"]')[0]
    attributes['net_transfer_record'] = transfer_record_element.xpath('span[@class="dataValue"]/span/a/text()').get().strip()

    # inspect_response(response,self)
    # parsing of "Coach for the season"
    attributes['coach_name'] = (
      response
        .xpath('//div[contains(@data-viewport, "Mitarbeiter")]//div[@class="container-hauptinfo"]/a/text()')
        .get()
        .strip()
    )

    yield {
      **base,
      **attributes
    }
