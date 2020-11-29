# -*- coding: utf-8 -*-

BOT_NAME = 'tfmkt'

SPIDER_MODULES = ['tfmkt.spiders']
NEWSPIDER_MODULE = 'tfmkt.spiders'

BASE_URL = 'https://www.transfermarkt.co.uk/wettbewerbe'

# if passed, this setting will be used to limit the scope of the scraping
# by filtering out paths from the site hierachy not defined here
SITE_TREE_FILTER = {
    '/wettbewerbe/europa': {
        '/premier-league/startseite/wettbewerb/GB1': {
            '/manchester-city/kader/verein/281/saison_id/2019':
                '/sergio-aguero/leistungsdaten/spieler/26399/plus/1?saison=2018'
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
USER_AGENT = 'tfmkt-scraper (https://github.com/dcaribou)'

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
