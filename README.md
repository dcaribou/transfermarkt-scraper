
![checks status](https://github.com/dcaribou/transfermarkt-scraper/workflows/Scrapy%20Contracts%20Checks/badge.svg)
![docker build status](https://github.com/dcaribou/transfermarkt-scraper/workflows/Dockerhub%20Image/badge.svg)
# transfermarkt-scraper

A web scraper for collecting data from [Transfermarkt](https://www.transfermarkt.co.uk/) website. The scraper recurses into the Transfermarkt hierarchy to reach all players' [detailed performance page](https://www.transfermarkt.co.uk/diogo-jota/leistungsdatendetails/spieler/340950/saison/2020/verein/0/liga/0/wettbewerb/GB1/pos/0/trainer_id/0/plus/1), and
extract appearances as JSON objects.

## run
This is a [scrapy](https://scrapy.org/) project, so it needs to be run with the
`scrapy` command line util. A conda `environment.yml` file is provided with a definition
for the necessary environment to run the scraper.
```console
conda env create -f environment.yml
conda activate transfermarkt-scraper
scrapy crawl partial -a site_map_file=sample_site_maps/ES1_athletic_bilbao_only.json
```
Alternatively you can use [`dcaribou/transfermarkt-scraper`](https://hub.docker.com/repository/docker/dcaribou/transfermarkt-scraper) image from dockerhub
```console
docker run \
    -ti dcaribou/transfermarkt-scraper \
    -v "$(pwd)"/sample_site_maps:/app/sample_site_maps \
    scrapy crawl partial -a site_map_file=sample_site_maps/ES1_athletic_bilbao_only.json
```
### auto
The `auto` spider recurses the Transfermarkt website hierarchy automatically for all reachable players. It can be invoked with the command
```console
scrapy crawl auto
```
> :warning: The `auto` spider scrapes the whole website hierarchy and therefore it will take quite some time to complete. Check the `partial` spider for scoped website scrapping.
> 
### partial
The `partial` spider uses a [site map file](sample_site_maps) to define the scrapping scope. The site map is a JSON representation of the site hierarchy that can be generated a single time by running
```console
scrapy crawl mapper > site_map.json
```
The `partial` spider can do scoped scraping now by using the file generated with the `mapper` crawler above
```console
scrapy crawl partial -a site_map_file=site_map.json
```
Some sample site map files are provided in [`sample_site_maps`](sample_site_maps).

## config
Check [setting.py](tfmkt/settings.py) for a reference of available configuration options

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
