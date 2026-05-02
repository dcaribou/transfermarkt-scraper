import json
import logging
import sys
from datetime import datetime

from crawlee import Request
from crawlee.crawlers import HttpCrawler

from tfmkt.common import DEFAULT_BASE_URL, load_parents, check_failures

logger = logging.getLogger(__name__)

POSITION_MAP = {
    1: 'GK', 2: 'SW', 3: 'CB', 4: 'LB', 5: 'RB',
    6: 'DM', 7: 'CM', 8: 'RM', 9: 'LM', 10: 'AM',
    11: 'RW', 12: 'LW', 13: 'SS', 14: 'CF',
}


def _format_stat(value):
    if value is None or value == 0:
        return ''
    return str(value)


def _format_date(date_str):
    if not date_str:
        return ''
    dt = datetime.fromisoformat(date_str)
    return dt.strftime('%m/%d/%y')


def _club_href(club_id, season_id):
    return f'/spielplan/verein/{club_id}/saison_id/{season_id}'


async def run(parents_arg=None, season=2024, base_url=None):
    base_url = base_url or DEFAULT_BASE_URL
    parents = load_parents(parents_arg)

    requests = []
    for parent in parents:
        player_id = parent['href'].rstrip('/').split('/')[-1]
        stats_href = parent['href'].replace('/profil/', '/leistungsdaten/')
        requests.append(
            Request.from_url(
                url=f"{base_url}/ceapi/performance-game/{player_id}",
                label='parse_api',
                user_data={'parent': parent, 'season': season, 'stats_href': stats_href},
            )
        )

    failures = []
    crawler = HttpCrawler()

    @crawler.failed_request_handler
    async def on_failed_request(context, error):
        failures.append((context.request.url, error))

    @crawler.router.default_handler
    async def parse_api(context) -> None:
        parent = context.request.user_data['parent']
        req_season = context.request.user_data['season']
        stats_href = context.request.user_data['stats_href']

        body = await context.http_response.read()
        data = json.loads(body)

        if not data.get('success'):
            logger.warning("API returned success=false for %s", context.request.url)
            return

        for perf in data.get('data', {}).get('performance', []):
            game_info = perf['gameInformation']

            if game_info['seasonId'] != req_season:
                continue

            general = perf['statistics']['generalStatistics']
            if general.get('participationState') != 'played':
                continue

            club = perf['clubsInformation']['club']
            opponent = perf['clubsInformation']['opponent']
            season_id = game_info['seasonId']

            if club['venue'] == 'home':
                result = f"{club['goalsTotal']}:{opponent['goalsTotal']}"
                venue = 'H'
            else:
                result = f"{opponent['goalsTotal']}:{club['goalsTotal']}"
                venue = 'A'

            goals = perf['statistics']['goalStatistics']
            cards = perf['statistics']['cardStatistics']
            playing_time = perf['statistics']['playingTimeStatistics']
            duels = perf['statistics']['duelStatistics']
            distribution = perf['statistics']['distributionStatistics']
            minutes = playing_time.get('playedMinutes')

            item = {
                'type': 'appearance',
                'href': stats_href,
                'parent': parent,
                'game_id': game_info['gameId'],
                'competition_code': game_info['competitionId'],
                'competition_group': game_info.get('competitionGroupId', ''),
                'matchday': game_info.get('gameDay', ''),
                'date': _format_date(game_info['date']['dateTimeUTC']),
                'venue': venue,
                'for': {'type': 'club', 'href': _club_href(club['clubId'], season_id)},
                'opponent': {'type': 'club', 'href': _club_href(opponent['clubId'], season_id)},
                'result': result,
                'pos': POSITION_MAP.get(general.get('positionId'), ''),
                'shirt_number': general.get('shirtNumber'),
                'is_captain': general.get('isCaptain'),
                'is_starting': playing_time.get('isStarting'),
                'on_at': (playing_time.get('substitutedIn') or {}).get('minute'),
                'off_at': (playing_time.get('substitutedOut') or {}).get('minute'),
                'goals': _format_stat(goals.get('goalsScoredTotal')),
                'assists': _format_stat(goals.get('assists')),
                'own_goals': goals.get('ownGoalsScored'),
                'yellow_cards': _format_stat(cards.get('yellowCardNet')),
                'second_yellow_cards': '',
                'red_cards': '',
                'minutes_played': f"{minutes}'" if minutes else '',
                'scoring_attempts': goals.get('scoringAttempts'),
                'scoring_attempts_on_goal': goals.get('scoringAttemptsOnGoal'),
                'tackles': duels.get('tackles'),
                'fouls_committed': duels.get('foulsCommitted'),
                'fouls_gained': duels.get('foulsGained'),
                'offsides': duels.get('offsides'),
                'passes': distribution.get('passes'),
                'pass_accuracy': distribution.get('passesReachedRatio'),
            }
            print(json.dumps(item), flush=True)

    await crawler.run(requests)
    check_failures(failures)
