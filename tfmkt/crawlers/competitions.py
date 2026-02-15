import json
import re

from crawlee import Request
from crawlee.crawlers import ParselCrawler
from inflection import parameterize, underscore

from tfmkt.common import DEFAULT_BASE_URL, load_parents, build_initial_requests, safe_strip


async def run(parents_arg=None, season=2024, base_url=None):
    base_url = base_url or DEFAULT_BASE_URL
    parents = load_parents(parents_arg)

    if not parents:
        parents = [{'type': 'root', 'href': ''}]

    requests = build_initial_requests(parents, season, base_url, label='parse', spider_name='competitions')

    international_competitions = {}

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

        new_requests = []
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

            href = "/wettbewerbe/national/wettbewerbe/" + country_id

            cb_data = {
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

            new_requests.append(
                Request.from_url(
                    url=base_url + href,
                    label='parse_competitions',
                    user_data={'base': cb_data},
                )
            )

        if new_requests:
            await context.add_requests(new_requests)

    @crawler.router.handler('parse_competitions')
    async def parse_competitions(context) -> None:
        base = context.request.user_data['base']

        domestic_competitions_tag = 'Domestic leagues & cups'
        parameterized_domestic_competitions_tag = underscore(parameterize(domestic_competitions_tag))
        international_competitions_tag = 'International competitions'

        boxes = context.selector.css('div.box')
        relevant_boxes = {}
        for box in boxes:
            box_header = safe_strip(box.css('h2.content-box-headline::text').get())
            if box_header in [domestic_competitions_tag, international_competitions_tag]:
                relevant_boxes[box_header] = box

        # parse domestic competitions
        box = relevant_boxes[domestic_competitions_tag]
        box_body = box.xpath('div[@class="responsive-table"]//tbody')[0]
        box_rows = box_body.xpath('tr')

        domestic_competitions = []

        for idx, row in enumerate(box_rows):
            tier = row.xpath('td/text()').get()
            if tier in [
                'First Tier',
                'Second Tier',
                'Third Tier',
                'Domestic Cup',
                'Domestic Super Cup',
            ]:
                parameterized_tier = underscore(parameterize(tier))
                competition_row = box_rows[idx + 1]
                competition_cell = competition_row.xpath('td/table//td')[1]
                competition_href = competition_cell.xpath('a/@href').get()
                competition_name = competition_cell.xpath('a/text()').get()
                domestic_competitions.append({
                    'type': 'competition',
                    'competition_type': parameterized_tier,
                    'competition_name': competition_name,
                    'href': competition_href,
                })

        # parse international competitions
        if 'parent' not in international_competitions:
            international_competitions['parent'] = base['parent']

        if international_competitions_tag in relevant_boxes:
            box = relevant_boxes[international_competitions_tag]
            box_rows = box.xpath('div[@class = "responsive-table"]//tr[contains(@class, "bg_blau_20")]')

            for row in box_rows:
                competition_href = row.xpath('td')[1].xpath('a/@href').get()
                competition_href_wo_season = re.sub(r'/saison_id/[0-9]{4}', '', competition_href)
                tier = row.xpath('td')[1].xpath('a/text()').get()
                parameterized_tier = underscore(parameterize(tier))

                international_competitions[parameterized_tier] = {
                    'type': 'competition',
                    'competition_name': tier,
                    'href': competition_href_wo_season,
                    'competition_type': parameterized_tier,
                }

        for competition in domestic_competitions:
            item = {
                'type': 'competition',
                **base,
                **competition,
            }
            print(json.dumps(item), flush=True)

    await crawler.run(requests)

    # Output deduped international competitions after crawl completes (replaces closed() hook)
    for key, value in international_competitions.items():
        if key == 'parent':
            continue
        competition = {
            'type': 'competition',
            'parent': international_competitions['parent'],
            **value,
        }
        print(json.dumps(competition), flush=True)
