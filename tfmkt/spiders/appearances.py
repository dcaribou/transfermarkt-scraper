from tfmkt.spiders.common import BaseSpider
from scrapy.shell import inspect_response # required for debugging
from inflection import parameterize, underscore
from urllib.parse import urlparse

class AppearancesSpider(BaseSpider):
  name = 'appearances'

  def parse(self, response, parent):
    """Parse player profile attributes and fetch "full stats" URL

    @url https://www.transfermarkt.co.uk/sergio-aguero/profil/spieler/26399
    @returns requests 1 1
    @cb_kwargs {"parent": "dummy"}
    """

    season = self.season

    full_stats_href = response.xpath('//a[contains(text(),"View full stats")]/@href').get()
    seasoned_full_stats_href = full_stats_href + f"/plus/0?saison={season}"

    yield response.follow(seasoned_full_stats_href, self.parse_stats, cb_kwargs={'parent': parent})

  def parse_stats(self, response, parent):
    """Parse player's full stats. From this page we collect all player appearances

    @url https://www.transfermarkt.co.uk/sergio-aguero/leistungsdaten/spieler/26399/plus/0?saison=2020
    @returns items 9
    @cb_kwargs {"parent": "dummy"}
    @scrapes assists competition_code date for goals href matchday minutes_played opponent parent pos red_cards result second_yellow_cards type venue yellow_cards
    """

    # inspect_response(response, self)
    # exit(1)

    def parse_stats_table(table):
        """Parses a table of player's statistics."""
        header_elements = [
            underscore(parameterize(header)) for header in
            table.css("th::text").getall() + table.css(
                "th > span::attr(title)"
            ).getall()
        ]
        # for some reason, sometimes transfermarket might call the matchday as spieltag
        # here we make sure that if that's the case we revert it back to matchday
        header_elements = [header if header != 'spieltag' else 'matchday' for header in header_elements]

        value_elements_matrix = [
          [ parse_stats_elem(element) for element in row.xpath('td') if parse_stats_elem(element) is not None
          ] for row in table.css('tr') if len(row.css('td').getall()) > 9 # TODO: find a way to include 'on the bench' and 'not in squad' occurrences
        ]

        for value_elements in value_elements_matrix:
          header_elements_len = len(header_elements)
          value_elements_len = len(value_elements)
          assert(header_elements_len == value_elements_len), f"Header ({header_elements}) - cell element ({value_elements}) mismatch at {response.url}"
          yield dict(zip(header_elements, value_elements))

    def parse_stats_elem(elem):
        """Parse an individual table cell"""

        self.logger.debug("Prasing element: %s", elem.get())

        # some cells include the club classification in the national league in brackets. for example, "Leeds (10.)"
        # these are at the same time unncessary and annoying to parse, as club information can be obtained
        # from the "shield" image. identify these cells by looking for descendents of the class 'tabellenplatz'
        has_classification_in_brackets = elem.xpath('*[@class = "tabellenplatz"]').get() is not None
        # club information is parsed from team "shields" using a separate logic from the rest
        # identify cells containing club shields
        has_shield_class = elem.css('img::attr(src)').get() is not None
        club_href = elem.xpath('a[contains(@href, "spielplan/verein")]/@href').get()
        result_href = elem.css('a.ergebnis-link::attr(href)').get()
        
        self.logger.debug("Extracted values: has_shield_class: %s, club_href: %s, result_href: %s", has_shield_class, club_href, result_href)
        
        if (
            (has_classification_in_brackets and club_href is None) or
            (club_href is not None and not has_shield_class) 
            ):
          self.logger.debug("Found club href without shield class, skipping")
          return None
        elif club_href is not None:
          self.logger.debug("Found club href: %s", club_href)
          return {'type': 'club', 'href': club_href}
        elif result_href is not None:
          self.logger.debug("Found result/game href: %s", result_href)
          return {'type': 'game', 'href': result_href}
        # finally, most columns can be parsed by extracting the text at the element's "last leaf"
        else:
          extracted_element = elem.xpath('string(.)').get().strip()
          self.logger.debug("Extracted element: %s", extracted_element)
          return extracted_element

    # stats tables are 'responsive-tables' (except the first one, which is
    # a summary table)

    competitions = response.css(
        'div.content-box-headline > a::attr(name)'
    ).getall()
    stats_tables = response.css('div.responsive-table')[1:]
    assert(len(competitions) == len(stats_tables))
    all_stats = {}
    for competition_name, table in zip(competitions, stats_tables):
      stats = list(parse_stats_table(table))
      all_stats[competition_name] = stats

    url = urlparse(response.url).path
    for competition_name, appearances in all_stats.items():
      for appearance in appearances:
        yield {
          'type': 'appearance',
          'href': url,
          'parent': parent,
          'competition_code': competition_name,
          **appearance
        }
