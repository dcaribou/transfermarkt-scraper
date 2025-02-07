from tfmkt.spiders.common import BaseSpider
from scrapy import Request
from scrapy.shell import inspect_response  # for debugging if needed
from urllib.parse import unquote, urlparse
import re
import json

class PlayersSpider(BaseSpider):
    name = 'players'

    def start_requests(self):
        """
        Override start_requests to clean each parent club URL:
         – remove any existing '/saison_id/…' segments, and then
         – append the desired season (e.g. 2025) once.
        """
        applicable_items = []
        for item in self.entrypoints:
            # Remove any existing '/saison_id/<number>' segment
            cleaned_href = re.sub(r'/saison_id/\d+', '', item.get('href', ''))
            # Set the cleaned URL back into the item and build the new seasonized URL.
            item['href'] = cleaned_href
            item['seasoned_href'] = f"{self.base_url}{cleaned_href}/saison_id/{self.season}"
            applicable_items.append(item)
        # Create and return a list of Request objects.
        return [
            Request(item['seasoned_href'], cb_kwargs={'parent': item})
            for item in applicable_items
        ]

    def parse(self, response, parent):
        """
        Parse the club page to collect all player URLs.
        We assume that exactly one responsive table is present.
        """
        # Use an XPath relative to the responsive-table element
        players_table = response.xpath("//div[@class='responsive-table']")
        assert len(players_table) == 1, "Expected exactly one responsive-table in the club page"
        players_table = players_table[0]

        # IMPORTANT: use a dot (.) to search relative to players_table.
        player_hrefs = players_table.xpath('.//table[@class="inline-table"]//td[@class="hauptlink"]/a/@href').getall()

        for href in player_hrefs:
            cb_kwargs = {
                'base': {
                    'type': 'player',
                    'href': href,  # the relative URL for the player profile
                    'parent': parent  # the parent's data from the clubs spider
                }
            }
            yield response.follow(href, self.parse_details, cb_kwargs=cb_kwargs)

    def parse_details(self, response, base):
        """
        Extract player details from the player's profile page.
        """
        attributes = {}

        # Extract the player header data.
        name_element = response.xpath("//h1[@class='data-header__headline-wrapper']")
        attributes["name"] = self.safe_strip("".join(name_element.xpath("text()").getall()))
        attributes["last_name"] = self.safe_strip(name_element.xpath("strong/text()").get())
        attributes["number"] = self.safe_strip(name_element.xpath("span/text()").get())

        # Extract additional player information.
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
        attributes['player_agent'] = {
            'href': response.xpath("//span[text()='Player agent:']/following::span[1]/a/@href").get(),
            'name': response.xpath("//span[text()='Player agent:']/following::span[1]/a/text()").get()
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

        # Handle market value information.
        current_market_value_text = self.safe_strip(response.xpath("//div[@class='tm-player-market-value-development__current-value']/text()").get())
        current_market_value_link = self.safe_strip(response.xpath("//div[@class='tm-player-market-value-development__current-value']/a/text()").get())
        attributes['current_market_value'] = current_market_value_text if current_market_value_text else current_market_value_link
        attributes['highest_market_value'] = self.safe_strip(response.xpath("//div[@class='tm-player-market-value-development__max-value']/text()").get())

        # Social media links.
        social_media_node = response.xpath("//span[text()='Social-Media:']/following::span[1]")
        if social_media_node:
            attributes['social_media'] = [elem.xpath('@href').get() for elem in social_media_node.xpath('div[@class="socialmedia-icons"]/a')]
        else:
            attributes['social_media'] = []

        # Parse market value history from the embedded graph.
        attributes['market_value_history'] = self.parse_market_history(response)

        # Extract a short code from the parent's URL.
        attributes['code'] = unquote(urlparse(base["href"]).path.split("/")[1])

        yield {**base, **attributes}

    def parse_market_history(self, response):
        """
        Parse player's market history from the embedded graph script.
        """
        pattern = re.compile(r'\'data\'\:.*\}\}]')
        try:
            script_text = response.xpath("//script[contains(., 'series')]/text()").re(pattern)[0]
            cleaned = '{' + script_text.replace("'", "\"") + '}'
            parsed_script = json.loads(cleaned.encode().decode('unicode_escape'))
            return parsed_script.get("data")
        except Exception as err:
            self.logger.warning("Failed to scrape market value history from %s", response.url)
            return None

    def safe_strip(self, word):
        return word.strip() if word else word
