# -*- coding: utf-8 -*-
BOT_NAME = 'tfmkt'

SPIDER_MODULES = ['tfmkt.spiders']
NEWSPIDER_MODULE = 'tfmkt.spiders'

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

CLOSESPIDER_PAGECOUNT = 0

LOG_LEVEL = 'ERROR'
