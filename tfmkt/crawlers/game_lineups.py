import json
import re

from crawlee import Request
from crawlee.crawlers import ParselCrawler

from tfmkt.common import DEFAULT_BASE_URL, load_parents, build_initial_requests, safe_strip


def _parse_age_from_text(text):
    """Extract age from text like '(34 years old)'."""
    if not text:
        return None
    match = re.search(r'\((\d+) years? old\)', text)
    return match.group(1) if match else None


def _parse_market_value(position_text):
    """Extract market value from position text like 'Centre-Back, €40.00m'."""
    if not position_text or ',' not in position_text:
        return None
    parts = position_text.split(',', 1)
    return safe_strip(parts[1]) if len(parts) > 1 else None


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
                    # Nationality flags are in td[2] of the number row
                    nationalities = e.xpath("./td[contains(@class, 'zentriert')]//img[contains(@class, 'flaggenrahmen')]/@title").getall()
                    if nationalities:
                        player['player_nationality'] = nationalities
                elif player_idx:
                    player['href'] = e.xpath("./td/a/@href").get()
                    player['name'] = e.xpath("./td/a/@title").get()
                    player['team_captain'] = 1 if e.xpath("./td/span/@title").get() else 0
                    # Age is in the text like "(34 years old)" in the player name cell
                    all_text = ''.join(e.xpath(".//td//text()").getall())
                    age = _parse_age_from_text(all_text)
                    if age:
                        player['player_age'] = age
                elif position_idx:
                    position_text = safe_strip(e.xpath("./td/text()").get())
                    position = position_text.split(',')[0] if position_text else ''
                    player['position'] = safe_strip(position)
                    # Market value is after the comma in the position text
                    market_value = _parse_market_value(position_text)
                    if market_value:
                        player['player_market_value'] = market_value
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
                    nationalities = e.xpath("./td[contains(@class, 'zentriert')]//img[contains(@class, 'flaggenrahmen')]/@title").getall()
                    if nationalities:
                        player['player_nationality'] = nationalities
                elif player_idx:
                    player['href'] = e.xpath("./td/a/@href").get()
                    player['name'] = e.xpath("./td/a/@title").get()
                    player['team_captain'] = 1 if e.xpath("./td/span/@title").get() else 0
                    all_text = ''.join(e.xpath(".//td//text()").getall())
                    age = _parse_age_from_text(all_text)
                    if age:
                        player['player_age'] = age
                elif position_idx:
                    position_text = safe_strip(e.xpath("./td/text()").get())
                    player['position'] = position_text.split(',')[0] if position_text else ''
                    market_value = _parse_market_value(position_text)
                    if market_value:
                        player['player_market_value'] = market_value

                if position_idx:
                    if i == 0:
                        lineups['home_club']['substitutes'].append(player)
                    else:
                        lineups['away_club']['substitutes'].append(player)

        # Extract manager info for each team
        # Managers are in separate "Manager" headline boxes (one per team)
        manager_boxes = sel.xpath(
            "//div[./h2[contains(@class, 'content-box-headline')] "
            "and normalize-space(./h2) = 'Manager']"
        )
        for i, box in enumerate(manager_boxes):
            club_key = 'home_club' if i == 0 else 'away_club'
            trainer_link = box.xpath(
                ".//a[@class='wichtig' and contains(@href, 'profil/trainer')]"
            )
            if trainer_link:
                manager = {
                    'manager_name': safe_strip(trainer_link.xpath("text()").get()),
                    'href': trainer_link.xpath("@href").get(),
                }
                mgr_nationality = box.xpath(
                    ".//img[contains(@class, 'flaggenrahmen')]/@title"
                ).getall()
                if mgr_nationality:
                    manager['manager_nationality'] = mgr_nationality
                lineups[club_key]['manager'] = manager

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
