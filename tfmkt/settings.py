# -*- coding: utf-8 -*-
from tfmkt.site_map import site_map

BOT_NAME = 'tfmkt'

SPIDER_MODULES = ['tfmkt.spiders']
NEWSPIDER_MODULE = 'tfmkt.spiders'

BASE_URL = 'https://www.transfermarkt.co.uk'

# if passed, this setting will be used to limit the scope of the scraping
# by filtering out paths from the site hierachy not defined here

# to use the automatically generated site map from site_map.py
# SITE_MAP = site_map

SITE_MAP = {
    # confederation
    '/wettbewerbe/europa': {
        # competition
        '/premier-league/startseite/wettbewerb/GB1': {
            # club
            '/fc-liverpool/startseite/verein/31/saison_id/2020': [
                # player
                '/diogo-jota/leistungsdaten/spieler/340950/plus/1'
            ]
        }
    },
    # 'amerika': {

    # },
    # 'asien': {

    # },
    # 'afrika': {
        
    # }
}

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'transfermarkt-scraper (https://github.com/dcaribou/transfermarkt-scraper)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

FEED_FORMAT = 'jsonlines'
FEED_URI = 'stdout:'

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
EXTENSIONS = {
   'scrapy.extensions.closespider.CloseSpider': 500
}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
   'tfmkt.pipelines.CleanAppearancePipeline': 300,
}

CLOSESPIDER_PAGECOUNT = 0

LOG_LEVEL = 'ERROR'
