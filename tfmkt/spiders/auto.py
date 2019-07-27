# -*- coding: utf-8 -*-
import scrapy
from scrapy.shell import inspect_response

class AutoSpider(scrapy.Spider):
    name = 'auto'
    start_urls = ['https://www.transfermarkt.co.uk/']

    def parse(self, response):
        """Parse Transfermarkt entrypoint page. From here we collect all confederations urls

        @url https://www.transfermarkt.co.uk
        @returns items 6 6
        @returns requests 4 6
        @scrapes confederation
        """
        confederations = response.css(
            'div.konfoederationenbox > a::attr(href)'
        ).getall()
        for confederation in confederations:
            object = {'confederation': confederation.split('/')[-1]}
            yield object
            yield response.follow(
                confederation,
                callback=self.parse_confederation,
                cb_kwargs=object
            )

    def parse_confederation(self, response, confederation='europa'):
        """Parse confederations page. From this page we collect all confederation's competitions urls

        @url https://www.transfermarkt.co.uk/wettbewerbe/europa
        @returns items 50 50
        @returns requests 50 50
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
            yield {
                'competition': {
                    'name': name,
                    'url': url,
                    'confederation': confederation
                }
            }
            yield response.follow(
                url,
                callback=self.parse_competition,
                cb_kwargs={'competition': name}
            )

    def parse_competition(self, response, competition='GB1'):
        """Parse competition page. From this page we collect all competition's teams urls

        @url https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1
        @returns items 20 20
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
                cb_kwargs={'team': name}
            )

    def parse_team(self, response, team='manchester-city'):
        """Parse team's page. From this page we collect all player's urls.

        @url https://www.transfermarkt.co.uk/manchester-city/kader/verein/281/saison_id/2019
        @returns items 26 26
        @returns requests 26 26
        @scrapes player
        """

        player_hrefs = response.css('a.spielprofil_tooltip::attr(href)').getall()
        without_duplicates = list(set(player_hrefs))
        for href in without_duplicates:
            name = href.split('/')[1]
            id = href.split('/')[-1]
            yield {
                'player': {
                    'name': name,
                    'id': id,
                    'url': href,
                    'team': team
                }
            }
            # we are interested on a player's detailed career statistics
            detailed_statistics = href + '/plus/1?saison=2018'
            yield response.follow(
                detailed_statistics,
                callback=self.parse_player
            )

    def parse_player(self, response):
        """Parse player's page. From this page finally collect all player appearances

        @url https://www.transfermarkt.co.uk/sergio-aguero/leistungsdaten/spieler/26399/plus/1?saison=2018
        @returns items 26 26
        @scrapes appearance
        """
        def parse_stats_table(table):

        # stats tables are 'responsive-tables' (except the first one, that is
        # a summary table)
        stats_tables = response.css('div.responsive-table')[1:]
