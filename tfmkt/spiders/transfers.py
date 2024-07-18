from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response
import re
import json


class PlayerTransfersSpider(BaseSpider):
    name = 'transfers'

    def parse(self, response, parent):
        """Parse player's page to collect transfer history URL.

        @url https://www.transfermarkt.co.uk/ayoze-perez/profil/spieler/246968
        @returns requests 1 1
        @cb_kwargs {"parent": "dummy"}
        """
        player_id = response.url.split('/')[-1]
        transfers_api_url = f"/ceapi/transferHistory/list/{player_id}"

        cb_kwargs = {
            'parent': parent
        }

        yield response.follow(transfers_api_url, self.parse_transfers, cb_kwargs=cb_kwargs)

    def parse_transfers(self, response, parent):
        """Extract player's transfer history from API response.

        @url https://www.transfermarkt.co.uk/ceapi/transferHistory/list/246968
        @returns items 7 7
        @cb_kwargs {"parent": {"type": "player", "href": "/ayoze-perez/profil/spieler/246968"}}
        @scrapes type href parent season date from to market_value fee
        """

        data = json.loads(response.text)

        for transfer in data['transfers']:
            yield {
                'type': 'transfer',
                'href': transfer['url'],
                'parent': parent,
                'season': transfer['season'],
                'date': transfer['dateUnformatted'],
                'from': {
                    'name': transfer['from']['clubName'],
                    'url': transfer['from']['href']
                },
                'to': {
                    'name': transfer['to']['clubName'],
                    'url': transfer['to']['href']
                },
                'market_value': transfer['marketValue'],
                'fee': transfer['fee']
            }