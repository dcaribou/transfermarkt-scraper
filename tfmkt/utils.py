def uri_params(params, spider):
    """uri_params is used by scrapy to generate additional parameters for URI generation.

    https://docs.scrapy.org/en/latest/topics/feed-exports.html?highlight=FEED_URI#std-setting-FEED_URI_PARAMS

    :param params: A dict with default parameters that can be enhanced with addtional keys.
    :type params: dict
    :return: A new dict with addtional keys.
    :rtype: Spider
    """
    return {**params, "season": spider.season}

def background_position_in_px_to_minute(px_x: int, px_y: int) -> int:
    """Convert background-position arguments from the "sb-sprite-uhr-klein" CSS class to the game minute.
    This CSS class uses some smartness that moves the this image around so as to choose the game minutes
    https://tmssl.akamaized.net/images/spielbericht/sb-sprite-uhr-k.png

    This function takes the image position in pixels and returns the game minute.

    :param px_x: "X" position in pixels
    :type px_x: int
    :param px_y: "Y" position in pixels
    :type px_y: int
    :return: The game minutes
    :rtype: int
    """

    n = 10 # number of columns in the matrix
    m = 13 # number of rows in the matrix
    h = 36 # size of the chronometer square in pixels

    x_offset = 0
    y_offset = 0

    matrix = [
        list(range((a-1)*n + 1, a*n + 1))
        for a in range(1, m)
    ]

    if abs(px_y) > h*(m - 1 - y_offset): # no data available
        return -1

    x = abs(px_x) / h
    assert x.is_integer()
    x = int(x) + x_offset

    y = abs(px_y) / h
    assert y.is_integer()
    y = int(y) + y_offset

    return matrix[y][x]
