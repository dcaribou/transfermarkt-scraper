![example workflow name](https://github.com/dcaribou/transfermarkt-scraper/workflows/Scrapy%20Contracts%20%Checks/badge.svg?branch=gh-actions)

## transfermarkt-scraper

A web scraper for collecting data from [Transfermarkt](https://www.transfermarkt.co.uk/) website. The scraper recurses into the Transfermarkt hierarchy to reach all players' [detailed performance page](https://www.transfermarkt.co.uk/diogo-jota/leistungsdatendetails/spieler/340950/saison/2020/verein/0/liga/0/wettbewerb/GB1/pos/0/trainer_id/0/plus/1), and
extract appearances as a JSON object.

### run
This is a [`scrapy`](https://scrapy.org/) project, so it needs to be run with the
`scrapy` command line util.
```console
scrapy crawl auto
```

### config
The website hierarchy to recurse can be trimmed by using the configuration `SITE_TREE_FILTER`.
```python
# if passed, this setting will be used to limit the scope of the scraping
# by filtering out paths from the site hierachy not defined here
SITE_TREE_FILTER = {
    # confederation
    '/wettbewerbe/europa': {
        # competition
        '/premier-league/startseite/wettbewerb/GB1': {
            # club
            '/fc-liverpool/startseite/verein/31/saison_id/2020':
                # player
                '/diogo-jota/leistungsdaten/spieler/340950/plus/1'
        }
    },
    # '/wettbewerbe/amerika': {},
    # '/wettbewerbe/asien': {},
    # '/wettbewerbe/afrika': {}
}
```

### example
Appearances data is extracted in JSON format. One JSON object is produced per stats table in the [detailed performance page](https://www.transfermarkt.co.uk/diogo-jota/leistungsdatendetails/spieler/340950/saison/2020/verein/0/liga/0/wettbewerb/GB1/pos/0/trainer_id/0/plus/1) and printed to the `stdout`.
```json
{
    "confederation": "europa",
    "domestic_competition": "GB1",
    "stats_competition": "FAC",
    "current_team": "fc-liverpool",
    "player_name": "diogo-jota",
    "stats": [
        {
            "matchday": "Third Round",
            "date": "2019-01-07",
            "home_team": "wolverhampton-wanderers",
            "away_team": "fc-liverpool",
            "result": "2:1",
            "pos": "CF",
            "goals": 0,
            "assists": "1",
            "own_goals": 0,
            "yellow_cards": 0,
            "second_yellow_cards": 0,
            "red_cards": 0,
            "substitutions_on": 0,
            "substitutions_off": "52'",
            "minutes_played": 52
        },
        {
            "matchday": "Sixth Round",
            "date": "2019-03-16",
            "home_team": "wolverhampton-wanderers",
            "away_team": "manchester-united",
            "result": "2:1",
            "pos": "CF",
            "goals": "1",
            "assists": 0,
            "own_goals": 0,
            "yellow_cards": 0,
            "second_yellow_cards": 0,
            "red_cards": 0,
            "substitutions_on": 0,
            "substitutions_off": "87'",
            "minutes_played": 87
        }
    ]
}
```



