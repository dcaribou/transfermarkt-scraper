# -*- coding: utf-8 -*-
BOT_NAME = 'tfmkt'

SPIDER_MODULES = ['tfmkt.spiders']
NEWSPIDER_MODULE = 'tfmkt.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Basic rate limiting - start conservative
DOWNLOAD_DELAY = 1  # Base delay between requests
RANDOMIZE_DOWNLOAD_DELAY = 0.5  # Random delay up to 50% of DOWNLOAD_DELAY

# AutoThrottle - dynamically adjusts delay based on response times and load
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1  # Initial delay
AUTOTHROTTLE_MAX_DELAY = 10  # Maximum delay if site is slow/overloaded  
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0  # Average number of requests being processed in parallel
AUTOTHROTTLE_DEBUG = False  # Enable to see throttling stats (set to True for monitoring)

# Concurrency settings - conservative for transfermarkt.de
CONCURRENT_REQUESTS = 8  # Total concurrent requests across all domains
CONCURRENT_REQUESTS_PER_DOMAIN = 2  # Max concurrent requests per domain (transfermarkt.de)

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

# User agent rotation to appear more natural
USER_AGENT = 'tfmkt (+http://www.yourdomain.com)'

# Additional settings for better scraping behavior
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Handle DNS timeouts
DNSCACHE_ENABLED = True
DNSCACHE_SIZE = 10000
DNS_TIMEOUT = 60

ROBOTSTXT_USER_AGENT="USER_AGENT='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'"