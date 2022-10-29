# https://docs.scrapy.org/en/latest/topics/feed-exports.html?highlight=FEED_URI#std-setting-FEED_URI_PARAMS
def uri_params(params, spider):
  """uri_params is used by scrapy to generate additional parameters for URI generation 

  Args:
      params (dict): A dict with default parameters that can be enhanced with addtional keys.
      spider (Spider): The spider instance that calls the function.

  Returns:
      (dict): A new dict with addtional keys.
  """
  return {**params, "season": spider.season}
