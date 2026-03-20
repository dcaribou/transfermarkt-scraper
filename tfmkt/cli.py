import argparse
import asyncio
import importlib

CRAWLER_MODULES = {
    'confederations': 'tfmkt.crawlers.confederations',
    'competitions': 'tfmkt.crawlers.competitions',
    'countries': 'tfmkt.crawlers.countries',
    'clubs': 'tfmkt.crawlers.clubs',
    'players': 'tfmkt.crawlers.players',
    'national_teams': 'tfmkt.crawlers.national_teams',
    'appearances': 'tfmkt.crawlers.appearances',
    'tournament_editions': 'tfmkt.crawlers.tournament_editions',
    'games': 'tfmkt.crawlers.games',
    'game_lineups': 'tfmkt.crawlers.game_lineups',
}


def main():
    parser = argparse.ArgumentParser(description='Transfermarkt scraper')
    parser.add_argument('crawler', choices=CRAWLER_MODULES.keys(), help='Crawler to run')
    parser.add_argument('-p', '--parents', default=None, help='Parents file path')
    parser.add_argument('-s', '--season', default=2024, type=int, help='Season year')
    parser.add_argument('--base-url', default=None, help='Base URL override')

    args = parser.parse_args()

    module = importlib.import_module(CRAWLER_MODULES[args.crawler])
    asyncio.run(module.run(
        parents_arg=args.parents,
        season=args.season,
        base_url=args.base_url,
    ))


if __name__ == '__main__':
    main()
