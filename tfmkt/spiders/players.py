from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response # required for debugging

class PlayersSpider(BaseSpider):
  name = 'players'

  def parse(self, response, parent):
      """Parse clubs's page to collect all player's urls.

        @url https://www.transfermarkt.co.uk/manchester-city/kader/verein/281/saison_id/2019
        @returns requests 34 34
        @cb_kwargs {"parent": "dummy"}
      """

      # inspect_response(response, self)
      # exit(1)

      players_table = response.xpath("//div[@class='responsive-table']")
      assert len(players_table) == 1

      players_table = players_table[0]

      player_hrefs = players_table.xpath("//tm-tooltip[@data-type='player']/div[1]/span/a/@href").getall()

      for href in player_hrefs:
          
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

    # uncommenting the two lines below will open a scrapy shell with the context of this request
    # when you run the crawler. this is useful for developing new extractors

    # inspect_response(response, self)
    # exit(1)

    # parse 'PLAYER DATA' section
    attributes = {}

    attributes['name_in_home_country'] = response.xpath("//span[text()='Name in home country:']/following::span[1]/text()").get()
    attributes['date_of_birth'] = response.xpath("//span[text()='Date of birth:']/following::span[1]//text()").get()
    attributes['place_of_birth'] = {
      'country': response.xpath("//span[text()='Place of birth:']/following::span[1]/span/img/@title").get(),
      'city': response.xpath("//span[text()='Place of birth:']/following::span[1]/span/text()").get()
    }
    attributes['age'] = response.xpath("//span[text()='Age:']/following::span[1]/text()").get()
    attributes['height'] = response.xpath("//span[text()='Height:']/following::span[1]/text()").get()
    attributes['citizenship'] = response.xpath("//span[text()='Citizenship:']/following::span[1]/img/@title").get()
    attributes['position'] = self.safe_strip(response.xpath("//span[text()='Position:']/following::span[1]/text()").get())
    attributes['player_agent'] = {
      'href': response.xpath("//span[text()='Player agent:']/following::span[1]/a/@href").get(),
      'name': response.xpath("//span[text()='Player agent:']/following::span[1]/a/text()").get()
    }
    attributes['current_club'] = {
      'href': response.xpath("//span[contains(text(),'Current club:')]/following::span[1]/a/@href").get()
    }
    attributes['foot'] = response.xpath("//span[text()='Foot:']/following::span[1]/text()").get()
    attributes['joined'] = response.xpath("//span[text()='Joined:']/following::span[1]/text()").get()
    attributes['contract_expires'] = self.safe_strip(response.xpath("//span[text()='Contract expires:']/following::span[1]/text()").get())
    attributes['day_of_last_contract_extension'] = response.xpath("//span[text()='Date of last contract extension:']/following::span[1]/text()").get()
    attributes['outfitter'] = response.xpath("//span[text()='Outfitter:']/following::span[1]/text()").get()
    attributes['current_market_value'] = self.safe_strip(response.xpath("//div[@class='marktwertentwicklung']//div[@class='zeile-oben']//div[@class='right-td']//a/text()").get())
    attributes['highest_market_value'] = self.safe_strip(response.xpath("//div[@class='marktwertentwicklung']//div[@class='zeile-unten']//div[@class='right-td']//text()").get())

    social_media_value_node = response.xpath("//span[text()='Social-Media:']/following::span[1]")
    if len(social_media_value_node) > 0:
      attributes['social_media'] = []
      for element in social_media_value_node.xpath('div[@class="socialmedia-icons"]/a'):
        href = element.xpath('@href').get()
        attributes['social_media'].append(
          href
        )

    yield {
      **base,
      **attributes
    }
