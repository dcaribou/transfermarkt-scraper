import re
from urllib.parse import urlparse
import os, sys
import json
import gzip
import typing
import scrapy
from scrapy import Request
from scrapy.shell import inspect_response  # for debugging if needed

default_base_url = 'https://www.transfermarkt.co.uk'

def read_lines(file_name: str, reading_fn: typing.Callable[[str], typing.IO[bytes]]) -> typing.List[dict]:
    with reading_fn(file_name) as f:
        lines = f.readlines()
        parents = [json.loads(line) for line in lines]
    return parents

class BaseSpider(scrapy.Spider):
    def __init__(self, base_url=None, parents=None, season=None):
        if base_url is not None:
            self.base_url = base_url
        else:
            self.base_url = default_base_url

        # Determine whether the parents file is gzip compressed.
        if parents is not None:
            extension = parents.split(".")[-1]
            self.gzip_compressed = (extension == "gz") if extension else False
        else:
            self.gzip_compressed = False

        # Load parent objects either from a file, zipped file, or stdin.
        if parents is not None:
            if self.gzip_compressed:
                parents = read_lines(parents, gzip.open)
            else:
                parents = read_lines(parents, open)
        elif not sys.stdin.isatty():
            parents = [json.loads(line) for line in sys.stdin]
        else:
            parents = self.scrape_parents()

        # Remove redundant second‑level “parent” entries.
        for parent in parents:
            if parent.get('parent') is not None:
                del parent['parent']

        # Use the provided season or default to 2025.
        if season:
            self.season = season
        else:
            self.season = 2025

        self.entrypoints = parents

    def scrape_parents(self):
        if not os.environ.get('SCRAPY_CHECK'):
            raise Exception("Backfilling is not yet supported, please provide a 'parents' file")
        else:
            return []

    def start_requests(self):
        applicable_items = []
        for item in self.entrypoints:
            # Use the (fixed) seasonize_entrypoin_href that cleans out any existing '/saison_id/…'
            item['seasoned_href'] = self.seasonize_entrypoin_href(item)
            applicable_items.append(item)
        return [
            Request(
                item['seasoned_href'],
                cb_kwargs={'parent': item}
            )
            for item in applicable_items
        ]

    def seasonize_entrypoin_href(self, item):
        """
        Build the URL for an entrypoint by appending the season.
        First, remove any existing '/saison_id/<digits>' parts from the item's href,
        then append the desired season. For competitions that are not domestic cups,
        if the cleaned href does not already contain '/plus/', we add it.
        """
        season = self.season
        # Remove any existing '/saison_id/...' segments:
        base_href = re.sub(r'/saison_id/\d+', '', item['href'])

        if item['type'] == 'club':
            seasonized_href = f"{self.base_url}{base_href}/saison_id/{season}"
        elif item['type'] == 'competition':
            # For domestic cups, change "wettbewerb" to "pokalwettbewerb"
            if item.get('competition_type') in ['domestic_cup', 'domestic_super_cup']:
                seasonized_href = f"{self.base_url}{base_href}?saison_id={season}".replace("wettbewerb", "pokalwettbewerb")
            else:
                # For league competitions (first tier, second tier, etc.), always use the plus form.
                if "/plus/" not in base_href:
                    seasonized_href = f"{self.base_url}{base_href}/plus/?saison_id={season}"
                else:
                    seasonized_href = f"{self.base_url}{base_href}?saison_id={season}"
        else:
            seasonized_href = f"{self.base_url}{base_href}"
        return seasonized_href

    def safe_strip(self, word):
        return word.strip() if word else word
