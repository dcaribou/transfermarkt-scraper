
# transfermarkt-scraper  ![checks status](https://github.com/dcaribou/transfermarkt-scraper/workflows/Scrapy%20Contracts%20Checks/badge.svg)

A web scraper for collecting data from [Transfermarkt](https://www.transfermarkt.co.uk/) website. The scraper recurses into the Transfermarkt hierarchy to reach all players' [detailed performance page](https://www.transfermarkt.co.uk/diogo-jota/leistungsdatendetails/spieler/340950/saison/2020/verein/0/liga/0/wettbewerb/GB1/pos/0/trainer_id/0/plus/1), and
extract appearances as a JSON object.

## run
This is a [`scrapy`](https://scrapy.org/) project, so it needs to be run with the
`scrapy` command line util.
### auto
The `auto` spider recurses the Transfermarkt website hierarchy automatically for all reachable players. It can be invoked with the command
```console
scrapy crawl auto
```
> :warning: The `auto` spider scrapes the whole website hierarchy and therefore it can take quite some time to run. Check the `partial` spider for scoped website scrapping.
### partial
The `partial` spider uses a `SITE_MAP` setting to define the scrapping scope. The `SITE_MAP` 
is a dict representation of the site hierarchy that can be generated a single time by running
```console
scrapy crawl mapper > tfmkt/site_map.py
```
By using this site map generated with the `mapper` crawler above, a `SITE_MAP` setting can be populated now in the [settings.py](tfmkt/settings.py) to do partial scraping with
```console
scrapy crawl partial
```
In [this example](tfmkt/site_map.py), a `SITE_MAP` is provided that can be used to scrape player statistics from Premier League's Aston Vila. Additional Premier League clubs can be commented out from the site map in order to have those scraped as well.

## config
The website hierarchy recursed can be trimmed by using the configuration `SITE_MAP`.
```python
# if passed, this setting will be used to limit the scope of the scraping
# by filtering out paths from the site hierachy that are not defined here
SITE_MAP = {
    # confederation
    '/wettbewerbe/europa': {
        # competition
        '/premier-league/startseite/wettbewerb/GB1': {
            # club
            '/fc-liverpool/startseite/verein/31/saison_id/2020': [
                # player
                '/diogo-jota/leistungsdaten/spieler/340950/plus/1'
            ]
        }
    },
    # '/wettbewerbe/amerika': {},
    # '/wettbewerbe/asien': {},
    # '/wettbewerbe/afrika': {}
}
```

## example
Appearances data is extracted in JSON format. One JSON object is produced per stats table in the [detailed performance page](https://www.transfermarkt.co.uk/diogo-jota/leistungsdatendetails/spieler/340950/saison/2020/verein/0/liga/0/wettbewerb/GB1/pos/0/trainer_id/0/plus/1) and printed to the `stdout`.
```json
{
    "confederation":"europa",
    "domestic_competition": "GB1",
    "stats_competition": "CL", 
    "current_team": "fc-liverpool",
    "player_name": "diogo-jota",
    "stats": [
        {"matchday": "Group D", "date": "2020-10-21", "home_team": "ajax-amsterdam", "away_team": "fc-liverpool", "result": "0:1", "pos": "LW", "goals": 0, "assists": 0, "own_goals": 0, "yellow_cards": 0, "second_yellow_cards": 0, "red_cards": 0, "substitutions_on": "60'", "substitutions_off": 0, "minutes_played": 30},
        {"matchday": "Group D", "date": "2020-10-27", "home_team": "fc-liverpool", "away_team": "fc-midtjylland", "result": "2:0", "pos": "RW", "goals": "1", "assists": 0, "own_goals": 0, "yellow_cards": 0, "second_yellow_cards": 0, "red_cards": 0, "substitutions_on": 0, "substitutions_off": "81'", "minutes_played": 81},
        {"matchday": "Group D", "date": "2020-11-03", "home_team": "atalanta-bergamo", "away_team": "fc-liverpool", "result": "0:5", "pos": "CF", "goals": "3", "assists": 0, "own_goals": 0, "yellow_cards": 0, "second_yellow_cards": 0, "red_cards": 0, "substitutions_on": 0, "substitutions_off": "65'", "minutes_played": 65},
        {"matchday": "Group D", "date": "2020-11-25", "home_team": "fc-liverpool", "away_team": "atalanta-bergamo", "result": "0:2", "pos": 0, "goals": 0, "assists": 0, "own_goals": 0, "yellow_cards": 0, "second_yellow_cards": 0, "red_cards": 0, "substitutions_on": "61'", "substitutions_off": 0, "minutes_played": 29},
        {"matchday": "Group D", "date": "2020-12-01", "home_team": "fc-liverpool", "away_team": "ajax-amsterdam", "result": "1:0", "pos": "CF", "goals": 0, "assists": 0, "own_goals": 0, "yellow_cards": 0, "second_yellow_cards": 0, "red_cards": 0, "substitutions_on": 0, "substitutions_off": "68'", "minutes_played": 68},
        {"matchday": "Group D", "date": "2020-12-09", "home_team": "fc-midtjylland", "away_team": "fc-liverpool", "result": "1:1", "pos": "LW", "goals": 0, "assists": 0, "own_goals": 0, "yellow_cards": 0, "second_yellow_cards": 0, "red_cards": 0, "substitutions_on": 0, "substitutions_off": "87'", "minutes_played": 87}
    ]
}
```



