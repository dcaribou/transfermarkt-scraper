# -*- coding: utf-8 -*-
import scrapy
from scrapy.shell import inspect_response
from inflection import parameterize, underscore

class AutoSpider(scrapy.Spider):
    name = 'auto'
    base_url = 'https://www.transfermarkt.co.uk/'

    def start_requests(self):
        # keys in the root of the site tree filter must be confederation urls
        # which are used as the starting point of the crawler
        base_url = self.settings.attributes['BASE_URL'].value
        relative_urls = self.settings.attributes['SITE_TREE_FILTER'].value.keys()
        for url in relative_urls:
            yield scrapy.Request(
                url=f"{base_url}{url}", 
                callback=self.parse,
                cb_kwargs={'relative_url':url}
            )

    def parse(self, response, confederation='europa', relative_url='/wettbewerbe/europa'):
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
            name = url.split('/')[-1]

            # limit scrapping scope
            scope_filter = self.settings.attributes.get('SITE_TREE_FILTER')
            # if there is a filter defined for this confederation, and the competition url
            # does not match to that in the filter, skip
            if scope_filter and type(scope_filter.value) == dict and scope_filter.value[relative_url] and url not in scope_filter.value[relative_url].keys():
                print('skipped')
                continue

            yield response.follow(
                url,
                callback=self.parse_competition,
                cb_kwargs={'confederation': confederation, 'competition': name}
            )

    def parse_competition(
        self,
        response,
        confederation='europa',
        competition='GB1'
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
            return True if table.css('th::text')[0].get() == 'Club' else False

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
            name = href.split('/')[1]
            yield response.follow(
                href,
                callback=self.parse_team,
                cb_kwargs={
                    'confederation': confederation,
                    'competition': competition,
                    'team': name
                }
            )

    def parse_team(
        self,
        response,
        confederation='europa',
        competition='GB1',
        team='manchester-city'
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
            yield scrapy.Request(
                url=(
                    self.base_url +
                    name +
                    '/leistungsdaten/spieler/' +
                    id +
                    '/plus/1?saison=2018'
                ),
                callback=self.parse_player,
                cb_kwargs={
                    'confederation': confederation,
                    'competition': competition,
                    'team': team,
                    'name': name
                }
            )

    def parse_player(
        self,
        response,
        confederation='europa',
        competition='GB1',
        team='manchester-city',
        name='sergio-aguero'
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

        def is_stats_table(table):
            """Checks whether a table is expected to contain player stats or not,
            by looking for the word 'Matchday' in the table headers. This is
            used for filtering season summary tables.
            """
            return False if len(table.css('div.summary')) > 0 else True

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
                'confederation': confederation,
                'domestic_competition': competition,
                'stats_competition': competition_name,
                'current_team': team,
                'player_name': name,
                'stats': stats
            }
