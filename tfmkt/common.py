import sys
import json
import gzip
import logging

from crawlee import Request

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = 'https://www.transfermarkt.co.uk'


def safe_strip(word):
    if word:
        return word.strip()
    return word


def read_lines(file_name, reading_fn):
    with reading_fn(file_name) as f:
        lines = f.readlines()
        return [json.loads(line) for line in lines]


def load_parents(parents_arg=None):
    if parents_arg is not None:
        extension = parents_arg.split(".")[-1]
        if extension == "gz":
            parents = read_lines(parents_arg, gzip.open)
        else:
            parents = read_lines(parents_arg, open)
    elif not sys.stdin.isatty():
        parents = [json.loads(line) for line in sys.stdin]
    else:
        return []

    # 2nd level parents are redundant
    for parent in parents:
        if parent.get('parent') is not None:
            del parent['parent']

    return parents


def seasonize_href(item, season, base_url):
    if item['type'] == 'club':
        return f"{base_url}{item['href']}/saison_id/{season}"
    elif item['type'] == 'competition':
        if item['competition_type'] == 'first_tier':
            return f"{base_url}{item['href']}/plus/0?saison_id={season}"
        elif item['competition_type'] in ['domestic_cup', 'domestic_super_cup']:
            return f"{base_url}{item['href']}?saison_id={season}".replace("wettbewerb", "pokalwettbewerb")
        else:
            return f"{base_url}{item['href']}?saison_id={season}"
    else:
        return f"{base_url}{item['href']}"


def build_initial_requests(parents, season, base_url, label, spider_name):
    requests = []
    for item in parents:
        # clubs extraction is best done on first_tier competition types only
        if spider_name == 'clubs' and item.get('competition_type') != 'first_tier':
            continue
        seasoned_href = seasonize_href(item, season, base_url)
        item['seasoned_href'] = seasoned_href
        requests.append(
            Request.from_url(
                url=seasoned_href,
                label=label,
                user_data={'parent': item},
            )
        )
    return requests
