
![checks status](https://github.com/dcaribou/transfermarkt-scraper/workflows/Scrapy%20Contracts%20Checks/badge.svg)
![docker build status](https://github.com/dcaribou/transfermarkt-scraper/workflows/Dockerhub%20Image/badge.svg)
# transfermarkt-scraper

A web scraper for collecting data from [Transfermarkt](https://www.transfermarkt.co.uk/) website. It recurses into the Transfermarkt hierarchy to find leagues, clubs, players and [appearances satistics](https://www.transfermarkt.co.uk/diogo-jota/leistungsdatendetails/spieler/340950/saison/2020/verein/0/liga/0/wettbewerb/GB1/pos/0/trainer_id/0/plus/1), and extracts them as JSON objects. 


`(root) |> Confederations |> Leagues |> Clubs |> (Players, Games) |> Appearances`

The scraper can be used to discover and refresh each one of these entities separately.

## run
This is a [scrapy](https://scrapy.org/) project, so it needs to be run with the
`scrapy` command line util. A conda `environment.yml` file is provided with a definition
for the necessary environment to run the scraper.

```console
# conda env create -f environment.yml
# conda activate transfermarkt-scraper

scrapy confederations > confederations.json
scrapy leagues -a parents=confederations.json > leagues.json

cat leagues | head -2 \
    | scrapy clubs \
    | scrapy players \
    | scrapy appearances
```
Alternatively you can also use [`dcaribou/transfermarkt-scraper`](https://hub.docker.com/repository/docker/dcaribou/transfermarkt-scraper) docker image

```console
docker run \
    -ti -v "$(pwd)"/.:/app \
    dcaribou/transfermarkt-scraper:main \
    scrapy crawl leagues -a parents=samples/confederations.json
```
Items are extracted in JSON format with one JSON object per item (confederation, league, club, player or appearance), which gets printed to the `stdout`. Samples of extracted data are provided in the [samples](samples) folder.

## config
Check [setting.py](tfmkt/settings.py) for a reference of available configuration options
