from io import BufferedReader
import scrapy
from scrapy import Request
from scrapy.shell import inspect_response  # required for debugging
import os, sys
import json
import gzip
import typing

default_base_url = 'https://www.transfermarkt.co.uk'

def read_lines(file_name: str, reading_fn: typing.Callable[[str], BufferedReader]) -> typing.List[dict]:
    """Reads JSON lines from a file."""
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

        # Determine if the parents file is gzip compressed.
        if parents is not None:
            extension = parents.split(".")[-1]
            if extension:
                self.gzip_compressed = (extension == "gz")
            else:
                self.gzip_compressed = False
        else:
            self.gzip_compressed = False

        # Load parent objects from a file (or stdin)
        if parents is not None:
            if self.gzip_compressed:
                parents = read_lines(parents, gzip.open)
            else:
                parents = read_lines(parents, open)
        elif not sys.stdin.isatty():
            parents = [json.loads(line) for line in sys.stdin]
        else:
            parents = self.scrape_parents()

        # Remove any second-level parent keys if present.
        for parent in parents:
            if parent.get('parent') is not None:
                del parent['parent']

        # Set season. (Default is now 2025 instead of 2022.)
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
        """
        Generate requests from entrypoints. Notice that we no longer filter out
        clubs that aren’t marked as 'first_tier'—all parent items are used.
        """
        applicable_items = []
        for item in self.entrypoints:
            item['seasoned_href'] = self.seasonize_entrypoin_href(item)
            applicable_items.append(item)
        return [
            Request(item['seasoned_href'], cb_kwargs={'parent': item})
            for item in applicable_items
        ]

    def seasonize_entrypoin_href(self, item):
        """
        Construct a seasonized URL for the entrypoint.
        
        - For clubs: append /saison_id/<season>
        - For competitions: if first_tier add /plus/0?saison_id=<season>,
          if domestic cups, replace wettbewerb with pokalwettbewerb,
          else just add ?saison_id=<season>.
        - Otherwise: just append the href.
        """
        season = self.season

        if item['type'] == 'club':
            seasonized_href = f"{self.base_url}{item['href']}/saison_id/{season}"
        elif item['type'] == 'competition':
            if item.get('competition_type') == 'first_tier':
                seasonized_href = f"{self.base_url}{item['href']}/plus/0?saison_id={season}"
            elif item.get('competition_type') in ['domestic_cup', 'domestic_super_cup']:
                seasonized_href = f"{self.base_url}{item['href']}?saison_id={season}".replace("wettbewerb", "pokalwettbewerb")
            else:
                seasonized_href = f"{self.base_url}{item['href']}?saison_id={season}"
        else:
            seasonized_href = f"{self.base_url}{item['href']}"

        return seasonized_href

    def safe_strip(self, word):
        if word:
            return word.strip()
        else:
            return word
