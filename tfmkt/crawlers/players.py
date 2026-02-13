import json
import re
import logging
from urllib.parse import unquote, urlparse

from crawlee import Request
from crawlee.crawlers import ParselCrawler

from tfmkt.common import DEFAULT_BASE_URL, load_parents, build_initial_requests, safe_strip

logger = logging.getLogger(__name__)


async def run(parents_arg=None, season=2024, base_url=None):
    base_url = base_url or DEFAULT_BASE_URL
    parents = load_parents(parents_arg)
    requests = build_initial_requests(parents, season, base_url, label='parse', spider_name='players')

    crawler = ParselCrawler()

    @crawler.router.handler('parse')
    async def parse(context) -> None:
        parent = context.request.user_data['parent']
        sel = context.selector

        players_table = sel.xpath("//div[@class='responsive-table']")
        assert len(players_table) == 1
        players_table = players_table[0]

        player_hrefs = players_table.xpath(
            '//table[@class="inline-table"]//td[@class="hauptlink"]/a/@href'
        ).getall()

        new_requests = []
        for href in player_hrefs:
            cb_data = {
                'type': 'player',
                'href': href,
                'parent': parent,
            }
            new_requests.append(
                Request.from_url(
                    url=base_url + href,
                    label='parse_details',
                    user_data={'base': cb_data},
                )
            )

        if new_requests:
            await context.add_requests(new_requests)

    @crawler.router.handler('parse_details')
    async def parse_details(context) -> None:
        base = context.request.user_data['base']
        sel = context.selector

        attributes = {}

        name_element = sel.xpath("//h1[@class='data-header__headline-wrapper']")
        attributes["name"] = safe_strip("".join(name_element.xpath("text()").getall()).strip())
        attributes["last_name"] = safe_strip(name_element.xpath("strong/text()").get())
        attributes["number"] = safe_strip(name_element.xpath("span/text()").get())

        attributes['name_in_home_country'] = sel.xpath(
            "//span[text()='Name in home country:']/following::span[1]/text()"
        ).get()
        attributes['date_of_birth'] = sel.xpath(
            "//span[@itemprop='birthDate']/text()"
        ).get().strip().split(" (")[0]
        attributes['place_of_birth'] = {
            'country': sel.xpath(
                "//span[text()='Place of birth:']/following::span[1]/span/img/@title"
            ).get(),
            'city': sel.xpath(
                "//span[text()='Place of birth:']/following::span[1]/span/text()"
            ).get(),
        }
        attributes['age'] = sel.xpath(
            "//span[@itemprop='birthDate']/text()"
        ).get().strip().split('(')[-1].split(')')[0]
        attributes['height'] = sel.xpath(
            "//span[text()='Height:']/following::span[1]/text()"
        ).get()
        attributes['citizenship'] = sel.xpath(
            "//span[text()='Citizenship:']/following::span[1]/img/@title"
        ).get()
        attributes['position'] = safe_strip(sel.xpath(
            "//span[text()='Position:']/following::span[1]/text()"
        ).get())
        attributes['player_agent'] = {
            'href': sel.xpath(
                "//span[text()='Player agent:']/following::span[1]/a/@href"
            ).get(),
            'name': sel.xpath(
                "//span[text()='Player agent:']/following::span[1]/a/text()"
            ).get(),
        }
        attributes['image_url'] = sel.xpath(
            "//img[@class='data-header__profile-image']/@src"
        ).get()
        attributes['current_club'] = {
            'href': sel.xpath(
                "//span[contains(text(),'Current club:')]/following::span[1]/a/@href"
            ).get(),
        }
        attributes['foot'] = sel.xpath(
            "//span[text()='Foot:']/following::span[1]/text()"
        ).get()
        attributes['joined'] = sel.xpath(
            "//span[text()='Joined:']/following::span[1]/text()"
        ).get()
        attributes['contract_expires'] = safe_strip(sel.xpath(
            "//span[text()='Contract expires:']/following::span[1]/text()"
        ).get())
        attributes['day_of_last_contract_extension'] = sel.xpath(
            "//span[text()='Date of last contract extension:']/following::span[1]/text()"
        ).get()
        attributes['outfitter'] = sel.xpath(
            "//span[text()='Outfitter:']/following::span[1]/text()"
        ).get()

        current_market_value_text = safe_strip(sel.xpath(
            "//div[@class='tm-player-market-value-development__current-value']/text()"
        ).get())
        current_market_value_link = safe_strip(sel.xpath(
            "//div[@class='tm-player-market-value-development__current-value']/a/text()"
        ).get())
        if current_market_value_text:
            attributes['current_market_value'] = current_market_value_text
        else:
            attributes['current_market_value'] = current_market_value_link
        attributes['highest_market_value'] = safe_strip(sel.xpath(
            "//div[@class='tm-player-market-value-development__max-value']/text()"
        ).get())

        social_media_value_node = sel.xpath(
            "//span[text()='Social-Media:']/following::span[1]"
        )
        if len(social_media_value_node) > 0:
            attributes['social_media'] = []
            for element in social_media_value_node.xpath('div[@class="socialmedia-icons"]/a'):
                href = element.xpath('@href').get()
                attributes['social_media'].append(href)

        attributes['market_value_history'] = parse_market_history(sel, context.request.url)
        attributes['code'] = unquote(urlparse(base["href"]).path.split("/")[1])

        item = {**base, **attributes}
        print(json.dumps(item), flush=True)

    await crawler.run(requests)


def parse_market_history(selector, url):
    pattern = re.compile(r'\'data\'\:.*\}\}]')
    try:
        parsed_script = json.loads(
            '{' + selector.xpath(
                "//script[contains(., 'series')]/text()"
            ).re(pattern)[0].replace("\'", "\"").encode().decode('unicode_escape') + '}'
        )
        return parsed_script["data"]
    except Exception:
        logger.warning("Failed to scrape market value history from %s", url)
        return None
