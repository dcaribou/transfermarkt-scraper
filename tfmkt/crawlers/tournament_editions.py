import json
import re

from crawlee import Request
from crawlee.crawlers import ParselCrawler

from tfmkt.common import DEFAULT_BASE_URL, load_parents, safe_strip


async def run(parents_arg=None, season=2024, base_url=None):
    base_url = base_url or DEFAULT_BASE_URL
    parents = load_parents(parents_arg)
    requests = []
    for item in parents:
        if item.get('type') != 'competition':
            continue
        href = item['href']
        erfolge_href = href.replace('/startseite/', '/erfolge/')
        requests.append(
            Request.from_url(
                url=f"{base_url}{erfolge_href}",
                label='parse',
                user_data={'parent': item},
            )
        )

    crawler = ParselCrawler()

    @crawler.router.handler('parse')
    async def parse(context) -> None:
        parent = context.request.user_data['parent']
        sel = context.selector

        table = sel.css('table.items')
        if not table:
            return

        for row in table[0].css('tr'):
            row_html = row.get()

            # Extrarow = competition section separator (skip)
            if 'extrarow' in row_html:
                continue

            cls = row.xpath('@class').get() or ''
            if 'odd' not in cls and 'even' not in cls:
                continue  # skip header rows

            cells = row.css('td')
            if len(cells) < 4:
                continue

            year_link = cells[0].css('a')
            year = safe_strip(year_link.css('::text').get())
            edition_href = year_link.xpath('@href').get()

            # Extract saison_id from edition href (e.g. /saison_id/2021)
            saison_match = re.search(r'saison_id/(\d+)', edition_href or '')
            season_id = saison_match.group(1) if saison_match else None

            # Strip saison_id from href to get canonical href
            canonical_href = re.sub(r'/saison_id/\d+', '', edition_href or '')

            winner_name = safe_strip(cells[2].css('a::text').get())
            winner_href = cells[2].css('a::attr(href)').get()
            winner_href = re.sub(r'/saison_id/\d+', '', winner_href or '') if winner_href else None
            winner_image = cells[1].css('img::attr(src)').get()

            coach_link = cells[3].css('a')
            coach_name = safe_strip(coach_link.css('::text').get())
            coach_href = coach_link.xpath('@href').get()

            item = {
                'type': 'tournament_edition',
                'href': canonical_href,
                'parent': parent,
                'year': year,
                'season': season_id,
                'winner': winner_name,
                'winner_href': winner_href,
                'winner_image': winner_image,
                'coach': coach_name,
                'coach_href': coach_href,
            }
            print(json.dumps(item), flush=True)

    await crawler.run(requests)
