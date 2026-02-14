import json

from crawlee import Request
from crawlee.crawlers import ParselCrawler

from tfmkt.common import DEFAULT_BASE_URL, load_parents, build_initial_requests, safe_strip


async def run(parents_arg=None, season=2024, base_url=None):
    base_url = base_url or DEFAULT_BASE_URL
    parents = load_parents(parents_arg)
    requests = build_initial_requests(parents, season, base_url, label='parse', spider_name='game_lineups')

    crawler = ParselCrawler()

    @crawler.router.handler('parse')
    async def parse(context) -> None:
        parent = context.request.user_data['parent']
        sel = context.selector

        lineups_url = parent['href'].replace('index', 'aufstellung')
        lineups_elements = sel.xpath(
            ".//div[./h2/@class = 'content-box-headline' and normalize-space(./h2/text()) = 'Line-Ups']"
            "/div[contains(@class, 'columns')]"
        )
        home_lineup = lineups_elements[0]
        away_lineup = lineups_elements[1]

        home_formation = safe_strip(home_lineup.xpath("./div[@class = 'row']/div/text()").get())
        away_formation = safe_strip(away_lineup.xpath("./div[@class = 'row']/div/text()").get())

        lineups = {
            'home_club': {
                'href': parent['home_club']['href'],
                'formation': home_formation,
                'starting_lineup': [],
                'substitutes': [],
            },
            'away_club': {
                'href': parent['away_club']['href'],
                'formation': away_formation,
                'starting_lineup': [],
                'substitutes': [],
            },
        }

        cb_data = {
            'parent': parent,
            'lineups': lineups,
            'href': lineups_url,
        }

        await context.add_requests([
            Request.from_url(
                url=base_url + lineups_url,
                label='parse_lineups',
                user_data={'base': cb_data},
            )
        ])

    @crawler.router.handler('parse_lineups')
    async def parse_lineups(context) -> None:
        base = context.request.user_data['base']
        sel = context.selector

        parent = base['parent']
        lineups = base['lineups']

        starting_elements = sel.xpath(
            "//div[./h2[contains(@class, 'content-box-headline')] and "
            "normalize-space(./h2/text()[2]) = 'Starting Line-up']//div[@class='responsive-table']"
        )
        substitutes_elements = sel.xpath(
            "//div[./h2[contains(@class, 'content-box-headline')] and "
            "normalize-space(./h2/text()[2]) = 'Substitutes']//div[@class='responsive-table']"
        )

        for i in range(len(starting_elements)):
            tr_elements = starting_elements[i].xpath("./table[@class = 'items']//tr")
            defenders_count = 0
            midfielders_count = 0
            forwards_count = 0
            for j in range(len(tr_elements)):
                e = tr_elements[j]
                idx = j % 3
                number_idx = idx == 0
                player_idx = idx == 1
                position_idx = idx == 2
                if number_idx:
                    player = {}
                    player['number'] = e.xpath("./td/div[@class = 'rn_nummer']/text()").get()
                elif player_idx:
                    player['href'] = e.xpath("./td/a/@href").get()
                    player['name'] = e.xpath("./td/a/@title").get()
                    player['team_captain'] = 1 if e.xpath("./td/span/@title").get() else 0
                elif position_idx:
                    position = safe_strip(e.xpath("./td/text()").get().split(',')[0])
                    player['position'] = position
                    if "Back" in position or "Defender" in position or "defender" in position:
                        defenders_count += 1
                    elif "Midfield" in position or "midfield" in position:
                        midfielders_count += 1
                    elif "Winger" in position or "Forward" in position or "Striker" in position or "Attack" in position:
                        forwards_count += 1

                if position_idx:
                    if i == 0:
                        lineups['home_club']['starting_lineup'].append(player)
                    else:
                        lineups['away_club']['starting_lineup'].append(player)

            formation = (
                f"{defenders_count}-{midfielders_count}-{forwards_count}"
                if (defenders_count + midfielders_count + forwards_count) == 10
                else None
            )
            if i == 0:
                if lineups['home_club']['formation'] is None:
                    lineups['home_club']['formation'] = formation
                else:
                    lineups['home_club']['formation'] = lineups['home_club']['formation'].split(':')[1].strip()
            else:
                if lineups['away_club']['formation'] is None:
                    lineups['away_club']['formation'] = formation
                else:
                    lineups['away_club']['formation'] = lineups['away_club']['formation'].split(':')[1].strip()

        for i in range(len(substitutes_elements)):
            tr_elements = substitutes_elements[i].xpath("./table[@class = 'items']//tr")
            for j in range(len(tr_elements)):
                e = tr_elements[j]
                idx = j % 3
                number_idx = idx == 0
                player_idx = idx == 1
                position_idx = idx == 2
                if number_idx:
                    player = {}
                    player['number'] = e.xpath("./td/div[@class = 'rn_nummer']/text()").get()
                elif player_idx:
                    player['href'] = e.xpath("./td/a/@href").get()
                    player['name'] = e.xpath("./td/a/@title").get()
                    player['team_captain'] = 1 if e.xpath("./td/span/@title").get() else 0
                elif position_idx:
                    player['position'] = safe_strip(e.xpath("./td/text()").get().split(',')[0])

                if position_idx:
                    if i == 0:
                        lineups['home_club']['substitutes'].append(player)
                    else:
                        lineups['away_club']['substitutes'].append(player)

        item = {
            'type': 'game_lineups',
            'parent': {
                'href': parent['href'],
                'type': parent['type'],
            },
            'href': base['href'],
            'game_id': parent['game_id'],
            'home_club': lineups['home_club'],
            'away_club': lineups['away_club'],
        }

        print(json.dumps(item), flush=True)

    await crawler.run(requests)
