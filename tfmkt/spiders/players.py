from tfmkt.spiders.common import BaseSpider
from scrapy.shell import Response
from scrapy.shell import inspect_response # required for debugging
from urllib.parse import unquote, urlparse
import re
import json

class PlayersSpider(BaseSpider):
  name = 'players'

  def parse(self, response, parent):
      """Parse clubs's page to collect all player's urls.

        @url https://www.transfermarkt.co.uk/sc-braga/startseite/verein/1075/saison_id/2019
        @returns requests 37 37
        @cb_kwargs {"parent": "dummy"}
      """

      # uncommenting the two lines below will open a scrapy shell with the context of this request
      # when you run the crawler. this is useful for developing new extractors

      # inspect_response(response, self)
      # exit(1)

      players_table = response.xpath("//div[@class='responsive-table']")
      assert len(players_table) == 1

      players_table = players_table[0]

      player_hrefs = players_table.xpath('//table[@class="inline-table"]//td[@class="hauptlink"]/a/@href').getall()

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

      @url https://www.transfermarkt.co.uk/steven-berghuis/profil/spieler/129554
      @returns items 1 1
      @cb_kwargs {"base": {"href": "some_href/code", "type": "player", "parent": {}}}
      @scrapes href type parent name last_name number
    """

    # uncommenting the two lines below will open a scrapy shell with the context of this request
    # when you run the crawler. this is useful for developing new extractors

    # inspect_response(response, self)
    # exit(1)

    # parse 'PLAYER DATA' section

    attributes = {}

    name_element = response.xpath("//h1[@class='data-header__headline-wrapper']")
    attributes["name"] = self.safe_strip("".join(name_element.xpath("text()").getall()).strip())
    attributes["last_name"] = self.safe_strip(name_element.xpath("strong/text()").get())
    attributes["number"] = self.safe_strip(name_element.xpath("span/text()").get())

    attributes['name_in_home_country'] = response.xpath("//span[text()='Name in home country:']/following::span[1]/text()").get()
    attributes['date_of_birth'] = response.xpath("//span[@itemprop='birthDate']/text()").get().strip().split(" (")[0]
    attributes['place_of_birth'] = {
      'country': response.xpath("//span[text()='Place of birth:']/following::span[1]/span/img/@title").get(),
      'city': response.xpath("//span[text()='Place of birth:']/following::span[1]/span/text()").get()
    }
    attributes['age'] = response.xpath("//span[@itemprop='birthDate']/text()").get().strip().split('(')[-1].split(')')[0]
    attributes['height'] = response.xpath("//span[text()='Height:']/following::span[1]/text()").get()
    attributes['citizenship'] = response.xpath("//span[text()='Citizenship:']/following::span[1]/img/@title").get()
    attributes['position'] = self.safe_strip(response.xpath("//span[text()='Position:']/following::span[1]/text()").get())
    
    # The agent name can either be inside the anchor tag, title of the anchor tag or 
    attributes['player_agent'] = {
      'href': response.xpath("//span[text()='Player agent:']/following::span[1]/a/@href").get(),
      'name': response.xpath("//span[text()='Player agent:']/following::span[1]/a/span[@class='cp']/@title").get() or  # Case 1: agent name in title attribute
              response.xpath("//span[text()='Player agent:']/following::span[1]/a/text()").get() or  # Case 2: agent name in <a> text
              response.xpath("//span[text()='Player agent:']/following::span[1]/span/text()").get()  # Case 3: agent name in <span> text without <a>
    }
    attributes['image_url'] = response.xpath("//img[@class='data-header__profile-image']/@src").get()
    attributes['current_club'] = {
      'href': response.xpath("//span[contains(text(),'Current club:')]/following::span[1]/a/@href").get()
    }
    attributes['foot'] = response.xpath("//span[text()='Foot:']/following::span[1]/text()").get()
    attributes['joined'] = response.xpath("//span[text()='Joined:']/following::span[1]/text()").get()
    attributes['contract_expires'] = self.safe_strip(response.xpath("//span[text()='Contract expires:']/following::span[1]/text()").get())
    attributes['day_of_last_contract_extension'] = response.xpath("//span[text()='Date of last contract extension:']/following::span[1]/text()").get()
    attributes['outfitter'] = response.xpath("//span[text()='Outfitter:']/following::span[1]/text()").get()

    # current_market_value_text = self.safe_strip(response.xpath("//div[@class='tm-player-market-value-development__current-value']/text()").get())
    # current_market_value_link = self.safe_strip(response.xpath("//div[@class='tm-player-market-value-development__current-value']/a/text()").get())
    
    # Get the meta description content
    meta_description = self.safe_strip(response.xpath("//meta[@name='description']/@content").get())
    
    # Use regex to extract the market value (e.g., €25k, €25m)
    check_match = re.search(r'Market value: (\€[\d\.]+[km]?)', meta_description)
    if check_match:
        market_value_text = check_match.group(1)  # e.g., '€25k'
        
        # Remove the Euro symbol
        market_value_text = market_value_text.replace('€', '').strip()
        
        # Handle the suffix (k = thousand, m = million)
        if 'k' in market_value_text:
            market_value = float(market_value_text.replace('k', '')) * 1000
            
        elif 'm' in market_value_text:
            market_value = float(market_value_text.replace('m', '')) * 1000000
        
        attributes['current_market_value'] = market_value
    else:
        attributes['current_market_value'] = None
    
    attributes['highest_market_value'] = self.safe_strip(response.xpath("//div[@class='tm-player-market-value-development__max-value']/text()").get())

    social_media_value_node = response.xpath("//span[text()='Social-Media:']/following::span[1]")
    if len(social_media_value_node) > 0:
      attributes['social_media'] = []
      for element in social_media_value_node.xpath('div[@class="socialmedia-icons"]/a'):
        href = element.xpath('@href').get()
        attributes['social_media'].append(
          href
        )


    # parse transfer history
    attributes['transfer_history'] = self.parse_transfer_history(response)

    attributes['code'] = unquote(urlparse(base["href"]).path.split("/")[1])

    # --- ON LOAN FROM ---
    attributes['on_loan_from'] = None
    on_loan_from = response.xpath(
        "//span[normalize-space(text())='On loan from:']"
        "/following-sibling::span[1]//a/@href"
    ).get()
    if on_loan_from:
        attributes['on_loan_from'] = on_loan_from.strip()


    # --- CONTRACT OPTION ---
    attributes['contract_option'] = None
    contract_option = response.xpath("//span[text()='Contract option:']/following::span[1]//text()").get()
    if contract_option:
        attributes['contract_option'] = contract_option.strip()

      # --- CONTRACT OPTION ---
    attributes['contract_there_expires'] = None
    contract_there_expires = response.xpath("//span[text()='Contract there expires:']/following::span[1]//text()").get()
    if contract_there_expires:
        attributes['contract_there_expires'] = contract_there_expires.strip()

    yield {
      **base,
      **attributes
    }

  def parse_transfer_history(self, response: Response):
    """
    Parse player's transfer history from the transfer history table
    """
    try:
      # Find the transfer history grid
      transfer_grid = response.xpath("//div[@class='grid tm-player-transfer-history-grid']")
      
      if not transfer_grid:
        self.logger.debug("No transfer history grid found for %s", response.url)
        return []
      
      transfers = []
      
      # Get all season cells (these mark the start of each transfer row)
      season_cells = transfer_grid.xpath(".//div[contains(@class, 'tm-player-transfer-history-grid__season')]")
      
      for season_cell in season_cells:
        # Season
        season = self.safe_strip(season_cell.xpath(".//text()").get())
        
        # Find the next sibling cells in order: date, old-club, new-club, market-value, fee
        current_cell = season_cell
        
        # Date cell (next sibling)
        date_cell = current_cell.xpath("following-sibling::div[contains(@class, 'tm-player-transfer-history-grid__date')][1]")
        date = self.safe_strip(date_cell.xpath(".//text()").get()) if date_cell else None
        
        # Left club cell (old-club)
        left_cell = current_cell.xpath("following-sibling::div[contains(@class, 'tm-player-transfer-history-grid__old-club')][1]")
        left_club = {
          'href': left_cell.xpath(".//a/@href").get() if left_cell else None,
          'name': self.safe_strip(left_cell.xpath(".//a/text()").get()) if left_cell else None
        }
        
        # Joined club cell (new-club)
        joined_cell = current_cell.xpath("following-sibling::div[contains(@class, 'tm-player-transfer-history-grid__new-club')][1]")
        joined_club = {
          'href': joined_cell.xpath(".//a/@href").get() if joined_cell else None,
          'name': self.safe_strip(joined_cell.xpath(".//a/text()").get()) if joined_cell else None
        }
        
        # Market Value cell
        mv_cell = current_cell.xpath("following-sibling::div[contains(@class, 'tm-player-transfer-history-grid__market-value')][1]")
        market_value = self.safe_strip(mv_cell.xpath(".//text()").get()) if mv_cell else None
        
        # Fee cell - this contains the transfer link with ID
        fee_cell = current_cell.xpath("following-sibling::div[contains(@class, 'tm-player-transfer-history-grid__fee')][1]")
        fee = None
        transfer_link = None
        transfer_id = None
        
        if fee_cell:
          # Get the transfer link from the fee cell
          transfer_link = fee_cell.xpath(".//a[contains(@class, 'tm-player-transfer-history-grid__link')]/@href").get()
          
          # Extract transfer ID from the href
          if transfer_link:
            # From your HTML: href="/everson/transfers/spieler/186032/transfer_id/3056873"
            transfer_id_match = re.search(r'/transfer_id/(\d+)', transfer_link)
            if transfer_id_match:
              transfer_id = transfer_id_match.group(1)
          
          # Get fee text (could be in the link or as plain text)
          fee_text = fee_cell.xpath(".//a/text()").get() or fee_cell.xpath(".//text()").get()
          fee = self.safe_strip(fee_text) if fee_text else None
        
        # Only add transfer if we have meaningful data
        if season or date or left_club['href'] or joined_club['href']:
          transfers.append({
            'season': season,
            'date': date,
            'left_club': left_club,
            'joined_club': joined_club,
            'market_value': market_value,
            'fee': fee,
            'transfer_id': transfer_id,
            'transfer_href': transfer_link
          })
      
      return transfers
      
    except Exception as err:
      self.logger.warning("Failed to scrape transfer history from %s: %s", response.url, str(err))
      return []

  def parse_market_history(self, response: Response):
    """
    Parse player's market history from the graph
    """
    pattern = re.compile('\'data\'\:.*\}\}]')

    try:
      parsed_script = json.loads(
        '{' + response.xpath("//script[contains(., 'series')]/text()").re(pattern)[0].replace("\'", "\"").encode().decode('unicode_escape') + '}'
      )
      return parsed_script["data"]
    except Exception as err:
      self.logger.warning("Failed to scrape market value history from %s", response.url)
      return None
