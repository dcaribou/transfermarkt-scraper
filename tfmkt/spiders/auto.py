# -*- coding: utf-8 -*-
import scrapy
from scrapy.shell import inspect_response
from inflection import parameterize, underscore

class AutoSpider(scrapy.Spider):
    name = 'auto'
    base_url = 'https://www.transfermarkt.co.uk/'
    start_urls = [base_url]

    def parse(self, response):
        """Parse Transfermarkt entrypoint page. From here we collect all confederations urls

        @url https://www.transfermarkt.co.uk
        @returns requests 1 2
        @scrapes confederation
        """
        confederations = response.css(
            'div.konfoederationenbox > a::attr(href)'
        ).getall()

        # lets limit scrapping to 'europa' for now
        confederations = [x for x in confederations if 'europa' in x]

        for confederation in confederations:
            object = {'confederation': confederation.split('/')[-1]}
            yield object
            yield response.follow(
                confederation,
                callback=self.parse_confederation,
                cb_kwargs=object
            )

    def parse_confederation(self, response, confederation='europa'):
        """Parse confederations page. From this page we collect all
        confederation's competitions urls

        @url https://www.transfermarkt.co.uk/wettbewerbe/europa
        @returns requests 1 2
        @scrapes competition
        """
        # competitions entries in the confederation page
        competitions = response.css(
            'table.items tbody tr'
        )
        # some entries in the table contain tier information
        # this rows have a single value, so we filter them for now by removing
        # rows with less than 2 values
        valid_rows = (
            x for x in competitions if len(x.css('td')) > 1
        )
        for competition in valid_rows:
            url = competition.css('a::attr(href)').getall()[1]
            name = url.split('/')[-1]

            # let's limit scrapping to the Premier League for now
            if name != 'GB1':
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
            yield {
                'team': {
                    'name': name,
                    'url': href,
                    'competition': competition
                }
            }
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
        @returns requests 24 24
        @scrapes player
        """

        # limit scrapping to manchester-city for now
        if team != 'manchester-city':
            return

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
                [element.strip() for element in row.xpath(
                    'td[not(descendant::*[local-name() = "img"])]'
                ).xpath('string(.)').getall()]
                for row in table.css('tr') if len(row.css('td').getall()) > 8
            ]

            for value_elements in value_elements_matrix:
                assert(len(header_elements) == len(value_elements))
                yield dict(zip(header_elements, value_elements))

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
