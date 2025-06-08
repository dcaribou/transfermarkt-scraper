# -*- coding: utf-8 -*-
BOT_NAME = 'tfmkt'

SPIDER_MODULES = ['tfmkt.spiders']
NEWSPIDER_MODULE = 'tfmkt.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

DOWNLOAD_DELAY = 2  # minimum download delay 
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_TARGET_CONCURRENCY = 1

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

# FAKEUSERAGENT_PROVIDERS = [
#     'scrapy_fake_useragent.providers.FakeUserAgentProvider',  # This is the first provider we'll try
#     'scrapy_fake_useragent.providers.FakerProvider',  # If FakeUserAgentProvider fails, we'll use faker to generate a user-agent string for us
#     'scrapy_fake_useragent.providers.FixedUserAgentProvider',  # Fall back to USER_AGENT value
# ]

# USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

# ROBOTSTXT_USER_AGENT="USER_AGENT='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'"