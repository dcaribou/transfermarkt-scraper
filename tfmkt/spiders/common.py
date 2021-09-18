import scrapy
from scrapy import Request
from scrapy.shell import inspect_response # required for debugging
import json
import os
import sys
import re

default_base_url = 'https://www.transfermarkt.co.uk'

class BaseSpider(scrapy.Spider):
  def __init__(self, base_url=None, parents=None):

    if base_url is not None:
      self.base_url = base_url
    else:
      self.base_url = default_base_url
    
    if parents is not None:
      with open(parents) as json_file:
        lines = json_file.readlines()
        parents = [ json.loads(line) for line in lines ]
    elif not sys.stdin.isatty():
        parents = [ json.loads(line) for line in sys.stdin ]
    else:
      parents = self.scrape_parents()

    # 2nd level parents are redundat
    for parent in parents:
      if parent.get('parent') is not None:
        del parent['parent']

    self.entrypoints = parents

  def scrape_parents(self):
    if not os.environ.get('SCRAPY_CHECK'):
      raise Exception("Backfilling is not yet supported, please provide a 'parents' file")
    else:
      return []

  def start_requests(self):

    for item in self.entrypoints:
      item['seasoned_href'] = self.seasonize_entrypoin_href(item)

    return [
      Request(
        item['seasoned_href'],
        cb_kwargs={
          'parent': item
        }
      )
      for item in self.entrypoints
    ]

  def seasonize_entrypoin_href(self, item):

    season = self.settings['SEASON']

    if item['type'] == 'club':
      seasonized_href = f"{self.base_url}{item['href']}/saison_id/{season}"
    elif item['type'] == 'competition':
      if item['competition_type'] == 'first_tier':
        seasonized_href = f"{self.base_url}{item['href']}/plus/0?saison_id={season}"
      else:
        seasonized_href = f"{self.base_url}{item['href']}?saison_id={season}".replace("wettbewerb", "pokalwettbewerb")
    else:
      seasonized_href = f"{self.base_url}{item['href']}"

    return seasonized_href

