import json
import re

from crawlee import Request
from crawlee.crawlers import ParselCrawler

from tfmkt.common import DEFAULT_BASE_URL, load_parents, build_initial_requests


async def run(parents_arg=None, season=2024, base_url=None):
    base_url = base_url or DEFAULT_BASE_URL
    parents = load_parents(parents_arg)

    if not parents:
        parents = [{'type': 'root', 'href': ''}]

    requests = build_initial_requests(parents, season, base_url, label='parse', spider_name='countries')

    seen_countries = set()

    crawler = ParselCrawler()

    @crawler.router.handler('parse')
    async def parse(context) -> None:
        parent = context.request.user_data.get('parent', {})

        current_url = context.request.url
        if '?page=' not in current_url:
            confederation_pages = {
                '/wettbewerbe/europa': 6,
                '/wettbewerbe/amerika': 3,
                '/wettbewerbe/asien': 3,
                '/wettbewerbe/afrika': 1,
            }

            confederation_path = None
            for path in confederation_pages:
                if path in current_url:
                    confederation_path = path
                    break

            if confederation_path:
                total_pages = confederation_pages[confederation_path]
                page_requests = []
                for page_num in range(2, total_pages + 1):
                    page_url = f"{base_url}{confederation_path}?page={page_num}"
                    page_requests.append(
                        Request.from_url(
                            url=page_url,
                            label='parse',
                            user_data={'parent': parent},
                        )
                    )
                if page_requests:
                    await context.add_requests(page_requests)

        table_rows = context.selector.css('table.items tbody tr.odd, table.items tbody tr.even')

        for row in table_rows:
            country_image_url = row.xpath('td')[1].css('img::attr(src)').get()
            country_name = row.xpath('td')[1].css('img::attr(title)').get()
            country_code = (
                row.xpath('td')[0]
                .xpath('table/tr/td')[1]
                .xpath('a/@href').get()
                .split('/')[-1]
            )

            total_clubs = row.css('td:nth-of-type(3)::text').get()
            total_players = row.css('td:nth-of-type(4)::text').get()
            average_age = row.css('td:nth-of-type(5)::text').get()
            foreigner_percentage = row.css('td:nth-of-type(6) a::text').get()
            average_market_value = row.css('td:nth-of-type(7)::text').get()
            total_value = row.css('td:nth-of-type(8)::text').get()

            matches = re.search(r'([0-9]+)\.png', country_image_url, re.IGNORECASE)
            country_id = matches.group(1)

            if country_id in seen_countries:
                continue
            seen_countries.add(country_id)

            href = "/wettbewerbe/national/wettbewerbe/" + country_id

            item = {
                'type': 'country',
                'href': href,
                'parent': parent,
                'country_id': country_id,
                'country_name': country_name,
                'country_code': country_code,
                'total_clubs': total_clubs,
                'total_players': total_players,
                'average_age': average_age,
                'foreigner_percentage': foreigner_percentage,
                'average_market_value': average_market_value,
                'total_value': total_value,
            }
            print(json.dumps(item), flush=True)

    await crawler.run(requests)
