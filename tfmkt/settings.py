# -*- coding: utf-8 -*-

BOT_NAME = 'tfmkt'

SPIDER_MODULES = ['tfmkt.spiders']
NEWSPIDER_MODULE = 'tfmkt.spiders'

ALLOWED_TO_CRAWL = {
    'europa': {
        'GB1': 'ALL',
        'L1': 'ALL',
        'ES1': 'ALL',
        'PO1': 'ALL',
        'SC1': 'ALL',
        'IT1': 'ALL',
        'FR1': 'ALL',
        'NL1': 'ALL'
    }
}

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'tfmkt-parser (https://github.com/dcaribou/tfmktscraper)'

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
