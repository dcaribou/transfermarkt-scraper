# -*- coding: utf-8 -*-
from urllib import parse
import scrapy
from scrapy.shell import inspect_response # required for debugging
from inflection import parameterize, underscore
import json

class PlayerSpider(scrapy.Spider):
    name = 'player'
    base_url = 'https://www.transfermarkt.co.uk/'

    def parse_player(
        self,
        response,
        confederation_url='europa',
        competition_url='GB1',
        team_url='/manchester-city/startseite/verein/281/saison_id/2020',
        player_url='sergio-aguero/leistungsdaten/spieler/26399/plus/1?saison=2018'
    ):
        """Parse player's page. From this page finally collect all player appearances

        @url https://www.transfermarkt.co.uk/sergio-aguero/leistungsdaten/spieler/26399/plus/1?saison=2018
        @returns items 5 5
        @scrapes stats
        """

        def parse_stats_table(table):
            """Parses a table of player's statistics."""
            header_elements = [
                underscore(parameterize(header)) for header in
                table.css("th::text").getall() + table.css(
                    "th > span::attr(title)"
                ).getall()
            ]

            value_elements_matrix = [
                [
                    parse_stats_elem(element).strip() for element in row.xpath(
                        'td[not(descendant::*[local-name() = "img"])]'
                    )
                ]
                for row in table.css('tr') if len(row.css('td').getall()) > 8
            ]

            for value_elements in value_elements_matrix:
                assert(len(header_elements) == len(value_elements))
                yield dict(zip(header_elements, value_elements))

        def parse_stats_elem(elem):
            """Parse an individual table cell"""

            team = elem.css('a.vereinprofil_tooltip::attr(href)').get()
            if team is not None:
                return team.split('/')[1]
            else:
                return elem.xpath('string(.)').get()

        # stats tables are 'responsive-tables' (except the first one, that is
        # a summary table)
        competitions = response.css(
            'div.table-header > a::attr(name)'
        ).getall()[1:]
        stats_tables = response.css('div.responsive-table')[1:]
        assert(len(competitions) == len(stats_tables))
        for competition_name, table in zip(competitions, stats_tables):
            stats = list(parse_stats_table(table))
            yield {
                'confederation': confederation_url.split('/')[-1],
                'domestic_competition': competition_url.split('/')[-1],
                'stats_competition': competition_name,
                'current_team': team_url.split('/')[1],
                'player_name': player_url.split('/')[1],
                'stats': stats
            }


class AutoSpider(PlayerSpider):
    """
    Recurse into transfermarkt website to reach player statistics page and extract
    data as JSON objects
    """
    name = 'auto'
    
    def __init__(self):
        self.site_map = {}
        super().__init__()
    
    def start_requests(self):
        # keys in the root of the site tree filter must be confederation urls
        # which are used as the starting point of the crawler
        base_url = self.settings.attributes['BASE_URL'].value
        relative_urls = self.settings.attributes['SITE_MAP'].value.keys()
        for url in relative_urls:
            # follow request
            yield scrapy.Request(
                url=f"{base_url}{url}", 
                callback=self.parse,
                cb_kwargs={'confederation_url': url}
            )

    def parse(self, response, confederation_url='/wettbewerbe/europa'):
        """Parse confederations page. From this page we collect all
        confederation's competitions urls

        @url https://www.transfermarkt.co.uk/wettbewerbe/europa
        @returns requests 25 25
        @scrapes competition
        """
        
        # competitions entries in the confederation page
        competitions = response.css(
            'table.items tbody tr:first-child a[title]::attr(href)'
        )
        for competition in competitions:
            url = competition.getall()[0]
            
            # limit scrapping scope
            scope_filter = self.settings.attributes.get('SITE_MAP')
            # if there is a filter defined for this confederation, and the competition url
            # does not match to that in the filter, skip
            if scope_filter and type(scope_filter.value) == dict and scope_filter.value[confederation_url] and url not in scope_filter.value[confederation_url].keys():
                continue

            yield response.follow(
                url,
                callback=self.parse_competition,
                cb_kwargs={
                    'confederation_url': confederation_url,
                    'competition_url': url
                }
            )

    def parse_competition(
        self,
        response,
        confederation_url='europa',
        competition_url='GB1'
    ):
        """Parse competition page. From this page we collect all competition's
        teams urls

        @url https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1
        @returns requests 20 20
        @scrapes team
        """

        def is_teams_table(table):
            """Checks whether a table is expected to contain teams information
            or not, by looking for the word 'Club' in the table headers.
            """
            return True if table.css('th::text')[0].get().lower() == 'club' else False

        def extract_team_href(row):
            """It extracts one team's href from a teams' table row"""
            return row.css('td')[1].css('a::attr(href)').get()

        # get all 'responsive-tabes' in the page
        page_tables = response.css(
            'div.responsive-table'
        )
        with_teams_info = [
            table for table in page_tables if is_teams_table(table)
        ]
        assert(len(with_teams_info) == 1)
        for row in with_teams_info[0].css('tbody tr'):
            href = extract_team_href(row)

            # follow urls
            yield response.follow(
                href,
                callback=self.parse_team,
                cb_kwargs={
                    'confederation_url': confederation_url,
                    'competition_url': competition_url,
                    'team_url': href
                }
            )

    def parse_team(
        self,
        response,
        confederation_url='europa',
        competition_url='GB1',
        team_url='manchester-city'
    ):
        """Parse team's page. From this page we collect all player's urls.

        @url https://www.transfermarkt.co.uk/manchester-city/kader/verein/281/saison_id/2019
        @returns requests 34 34
        @scrapes player
        """
        
        player_hrefs = response.css(
            'a.spielprofil_tooltip::attr(href)'
        ).getall()
        without_duplicates = list(set(player_hrefs))
        for href in without_duplicates:
            name = href.split('/')[1]
            id = href.split('/')[-1]
            # we are interested on a player's detailed career statistics
            relative_url = name + '/leistungsdaten/spieler/' + id + '/plus/1?saison=2018'

            yield scrapy.Request(
                url=(
                    self.base_url +
                    relative_url
                ),
                callback=self.parse_player,
                cb_kwargs={
                    'confederation_url': confederation_url,
                    'competition_url': competition_url,
                    'team_url': team_url,
                    'player_url': relative_url
                }
            )

class MapperSpider(AutoSpider):
    """
    Recurse into transfermarkt website to create JSON representation of the website hierachy.
    The result of the MapSpider can be used in the SITE_MAP setting to trim the AutoSpider
    srapping scope. 
    """
    name = 'mapper'

    def parse(self, response, confederation_url='/wettbewerbe/europa'):
        # record url to the site map
        self.site_map.update({confederation_url: {}})
        return super().parse(response, confederation_url)

    def parse_competition(self, response, confederation_url, competition_url):
        # record url to the site map
        site_map_confederation = self.site_map[confederation_url]
        site_map_confederation.update({competition_url: {}})
        self.site_map[confederation_url] = site_map_confederation

        return super().parse_competition(response, confederation_url=confederation_url, competition_url=competition_url)

    def parse_team(self, response, confederation_url, competition_url, team_url):
        # record url to the site map
        site_map_teams = self.site_map[confederation_url][competition_url]
        site_map_teams.update({team_url: []})
        self.site_map[confederation_url][competition_url] = site_map_teams

        return super().parse_team(response, confederation_url=confederation_url, competition_url=competition_url, team_url=team_url)
    
    def parse_player(self, response, confederation_url, competition_url, team_url, player_url):
        self.site_map[confederation_url][competition_url][team_url].append(
            player_url
        )
        return super().parse_player(response, confederation_url=confederation_url, competition_url=competition_url, team_url=team_url, player_url=player_url)

    @staticmethod
    def close(spider, reason):
        print(json.dumps(spider.site_map, indent=4, sort_keys=True))

class PartialSpider(PlayerSpider):
    """
    Takes a site representation dict from the SITE_MAP setting and scrapes player statistics
    for that tree.
    """
    name = 'partial'

    def start_requests(self):

        base_url = self.settings.attributes['BASE_URL'].value
        site_tree = self.settings.attributes['SITE_MAP'].value

        for confederation_url, competition_urls in site_tree.items():
            for competition_url, team_urls in competition_urls.items():
                for team_url, player_urls in team_urls.items():
                    for player_url in player_urls:
                        yield scrapy.Request(
                            url=f"{base_url}/{player_url}",
                            callback=self.parse_player,
                            cb_kwargs={
                                'confederation_url': confederation_url,
                                'competition_url': competition_url,
                                'team_url': team_url,
                                'player_url': player_url
                            }
                        )
