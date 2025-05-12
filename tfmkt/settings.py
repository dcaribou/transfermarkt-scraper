# -*- coding: utf-8 -*-
BOT_NAME = 'tfmkt'

SPIDER_MODULES = ['tfmkt.spiders']
NEWSPIDER_MODULE = 'tfmkt.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

FEED_FORMAT = 'jsonlines'
FEED_URI = 'stdout:'

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
EXTENSIONS = {
   'scrapy.extensions.closespider.CloseSpider': 500
}
DOWNLOADER_MIDDLEWARES = {
   'scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware': 500
}

CLOSESPIDER_PAGECOUNT = 0

LOG_LEVEL = 'ERROR'

# HttpCacheMiddleware settings
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
HTTPCACHE_ENABLED = True
HTTPCACHE_DIR = 'httpcache'

# https://docs.scrapy.org/en/latest/topics/request-response.html?highlight=REQUEST_FINGERPRINTER_IMPLEMENTATION#std-setting-REQUEST_FINGERPRINTER_IMPLEMENTATION
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
