import json
import re
from urllib.parse import unquote, urlparse

from crawlee import Request
from crawlee.crawlers import ParselCrawler
from tfmkt.common import DEFAULT_BASE_URL, load_parents, build_initial_requests, safe_strip


async def run(parents_arg=None, season=2024, base_url=None):
    base_url = base_url or DEFAULT_BASE_URL
    parents = load_parents(parents_arg)
    requests = build_initial_requests(parents, season, base_url, label='parse', spider_name='national_teams')

    crawler = ParselCrawler()

    @crawler.router.handler('parse')
    async def parse(context) -> None:
        parent = context.request.user_data['parent']
        sel = context.selector

        # Find the "National teams" section: a div.box containing p.langer-text with "National teams"
        national_teams_box = sel.xpath(
            '//p[contains(@class,"langer-text") and contains(text(),"National teams")]/ancestor::div[contains(@class,"box")]'
        )
        if not national_teams_box:
            return

        # Get the first team link (senior team) — the list items contain a elements
        team_links = national_teams_box.xpath('.//li/a[contains(@href, "/startseite/verein/")]')
        if not team_links:
            return

        team_link = team_links[0]
        href = team_link.xpath('@href').get()
        # Strip season from href if present
        href = re.sub(r'/saison_id/[0-9]{4}$', '', href)

        cb_data = {
            'type': 'national_team',
            'href': href,
            'parent': parent,
        }

        await context.add_requests([
            Request.from_url(
                url=f"{base_url}{href}/saison_id/{season}",
                label='parse_details',
                user_data={'base': cb_data},
            )
        ])

    @crawler.router.handler('parse_details')
    async def parse_details(context) -> None:
        base = context.request.user_data['base']
        sel = context.selector

        attributes = {}

        attributes['name'] = safe_strip(
            sel.xpath("//h1[contains(@class,'data-header__headline-wrapper')]/text()").get()
        )

        attributes['team_image_url'] = sel.xpath(
            "//div[contains(@class, 'data-header__profile-container')]//img/@src"
        ).get()

        attributes['squad_size'] = safe_strip(
            sel.xpath("//li[contains(text(),'Squad size:')]/span/text()").get()
        )
        attributes['average_age'] = safe_strip(
            sel.xpath("//li[contains(text(),'Average age:')]/span/text()").get()
        )

        foreigners_element = sel.xpath("//li[contains(text(),'Foreigners:')]")
        if foreigners_element:
            attributes['foreigners_number'] = safe_strip(
                foreigners_element.xpath("span/a/text()").get()
            )
            attributes['foreigners_percentage'] = safe_strip(
                foreigners_element.xpath("span/span/text()").get()
            )

        market_value_el = sel.css('a.data-header__market-value-wrapper')
        if market_value_el:
            # Combine text from spans: "€", "1.34", "bn" -> "€1.34bn"
            parts = market_value_el.css('span.waehrung::text').getall()
            number = market_value_el.xpath('text()').get()
            if parts and number:
                attributes['total_market_value'] = f"{parts[0]}{number.strip()}{parts[1] if len(parts) > 1 else ''}"
            else:
                attributes['total_market_value'] = safe_strip(''.join(market_value_el.xpath('.//text()').getall()))
        else:
            attributes['total_market_value'] = sel.css('div.dataMarktwert a::text').get()

        # Coach info
        coach_link = sel.xpath(
            "//h2[contains(text(), 'Coach')]/..//a[contains(@href, 'profil/trainer')]"
        )
        if coach_link:
            attributes['coach_name'] = coach_link[0].xpath('@title').get()
            attributes['coach_href'] = coach_link[0].xpath('@href').get()

        # Confederation
        attributes['confederation'] = safe_strip(
            sel.xpath("//li[contains(text(),'Confederation:')]//span/text()").get()
        )

        # FIFA World ranking (note: lowercase 'r' on the site)
        fifa_text = safe_strip(
            sel.xpath("//li[contains(text(),'FIFA World ranking:')]//a/text()").get()
        )
        if fifa_text:
            # Extract number from "Pos 4" format
            match = re.search(r'(\d+)', fifa_text)
            attributes['fifa_ranking'] = match.group(1) if match else fifa_text
        else:
            attributes['fifa_ranking'] = None

        attributes['code'] = unquote(urlparse(base["href"]).path.split("/")[1])

        item = {**base, **attributes}
        print(json.dumps(item), flush=True)

    await crawler.run(requests)
