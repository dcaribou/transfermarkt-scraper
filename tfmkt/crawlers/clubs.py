import json
import re
from urllib.parse import unquote, urlparse

from crawlee import Request
from crawlee.crawlers import ParselCrawler

from tfmkt.common import DEFAULT_BASE_URL, load_parents, build_initial_requests, safe_strip


async def run(parents_arg=None, season=2024, base_url=None):
    base_url = base_url or DEFAULT_BASE_URL
    parents = load_parents(parents_arg)
    requests = build_initial_requests(parents, season, base_url, label='parse', spider_name='clubs')

    crawler = ParselCrawler()

    @crawler.router.handler('parse')
    async def parse(context) -> None:
        parent = context.request.user_data['parent']

        def is_teams_table(table):
            return table.css('th::text')[0].get().lower() == 'club'

        def extract_team_href(row):
            return row.css('td')[1].css('a::attr(href)').get()

        page_tables = context.selector.css('div.responsive-table')
        with_teams_info = [table for table in page_tables if is_teams_table(table)]
        assert len(with_teams_info) == 1

        new_requests = []
        for row in with_teams_info[0].css('tbody tr'):
            href = extract_team_href(row)
            href_strip_season = re.sub('/saison_id/[0-9]{4}$', '', href)

            cb_data = {
                'type': 'club',
                'href': href_strip_season,
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

        attributes['total_market_value'] = sel.css('div.dataMarktwert a::text').get()

        attributes['squad_size'] = safe_strip(
            sel.xpath("//li[contains(text(),'Squad size:')]/span/text()").get()
        )
        attributes['average_age'] = safe_strip(
            sel.xpath("//li[contains(text(),'Average age:')]/span/text()").get()
        )

        foreigners_element = sel.xpath("//li[contains(text(),'Foreigners:')]")[0]
        attributes['foreigners_number'] = safe_strip(foreigners_element.xpath("span/a/text()").get())
        attributes['foreigners_percentage'] = safe_strip(
            foreigners_element.xpath("span/span/text()").get()
        )

        attributes['national_team_players'] = safe_strip(
            sel.xpath("//li[contains(text(),'National team players:')]/span/a/text()").get()
        )

        stadium_element = sel.xpath("//li[contains(text(),'Stadium:')]")[0]
        attributes['stadium_name'] = safe_strip(stadium_element.xpath("span/a/text()").get())
        attributes['stadium_seats'] = safe_strip(stadium_element.xpath("span/span/text()").get())

        attributes['net_transfer_record'] = safe_strip(
            sel.xpath("//li[contains(text(),'Current transfer record:')]/span/span/a/text()").get()
        )

        # Coach info from the "Coach for the season" section
        coach_link = sel.xpath(
            "//h2[contains(text(), 'Coach')]/..//a[contains(@href, 'profil/trainer')]"
        )
        if coach_link:
            attributes['coach_name'] = coach_link[0].xpath('@title').get()
            attributes['coach_href'] = coach_link[0].xpath('@href').get()
        else:
            # Fallback to legacy Mitarbeiter viewport selector
            coach_element = sel.xpath(
                '//div[contains(@data-viewport, "Mitarbeiter")]//div[@class="container-hauptinfo"]/a'
            )
            attributes['coach_name'] = coach_element.xpath('text()').get()
            attributes['coach_href'] = coach_element.xpath('@href').get()

        attributes['club_image_url'] = sel.xpath(
            "//div[contains(@class, 'data-header__profile-container')]//img/@src"
        ).get()

        attributes['league_position'] = safe_strip(
            sel.xpath("//li[contains(text(),'Table position:')]/span/text()").get()
        )

        attributes['code'] = unquote(urlparse(base["href"]).path.split("/")[1])
        attributes['name'] = safe_strip(
            sel.xpath("//span[@itemprop='legalName']/text()").get()
        ) or safe_strip(
            sel.xpath('//h1[@class="data-header__headline-wrapper data-header__headline-wrapper--oswald"]/text()').get()
        )

        for key, value in attributes.items():
            if value:
                attributes[key] = value.strip()

        item = {**base, **attributes}
        print(json.dumps(item), flush=True)

    await crawler.run(requests)
