
![checks status](https://github.com/dcaribou/transfermarkt-scraper/workflows/Scrapy%20Contracts%20Checks/badge.svg)
![docker build status](https://github.com/dcaribou/transfermarkt-scraper/workflows/Dockerhub%20Image/badge.svg)
# transfermarkt-scraper

A web scraper for collecting data from [Transfermarkt](https://www.transfermarkt.co.uk/) website. It recurses into the Transfermarkt hierarchy to find
[leagues](https://www.transfermarkt.co.uk/wettbewerbe/europa), 
[games](https://www.transfermarkt.co.uk/premier-league/gesamtspielplan/wettbewerb/GB1/saison_id/2020),
[clubs](https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1),
[players](https://www.transfermarkt.co.uk/manchester-city/kader/verein/281/saison_id/2019) and [appearances](https://www.transfermarkt.co.uk/sergio-aguero/leistungsdaten/spieler/26399), and extract them as JSON objects. 

```console
====> Confederations ====> Leagues ====> (Clubs, Games) ====> Players ====> Appearances
```

Each one of these entities can be discovered and refresh separately by invoking the corresponding crawler.

## run
This is a [scrapy](https://scrapy.org/) project, so it needs to be run with the
`scrapy` command line util. A conda `environment.yml` file is provided with a definition
for the necessary environment to run the scraper.

```console
# create and activate conda environment
conda env create -f environment.yml
conda activate transfermarkt-scraper

# discover confederantions and leagues on separate invokations
scrapy crawl confederations > confederations.json
scrapy crawl leagues -a parents=confederations.json > leagues.json

# you can use intermediate files or pipe crawlers one after the other to traverse hierarchy 
cat leagues | head -2 \
    | scrapy crawl clubs \
    | scrapy crawl players \
    | scrapy crawl appearances
```

Alternatively you can also use [`dcaribou/transfermarkt-scraper`](https://hub.docker.com/repository/docker/dcaribou/transfermarkt-scraper) docker image

```console
docker run \
    -ti -v "$(pwd)"/.:/app \
    dcaribou/transfermarkt-scraper:main \
    scrapy crawl leagues -a parents=samples/confederations.json
```
> :warning: When using this scraper please identify your project accordingly by using a custom user agent. You can pass the user agent string using the `USER_AGENT` scrapy setting. For example, `scrapy crawl players -s USER_AGENT=<your user agent> `
 
Items are extracted in JSON format with one JSON object per item (confederation, league, club, player or appearance), which gets printed to the `stdout`. Samples of extracted data are provided in the [samples](samples) folder.

Check out [player-scores](https://github.com/dcaribou/player-scores) to see `transfermarkt-scraper` in action on a real analytics project.

## config
Check [setting.py](tfmkt/settings.py) for a reference of available configuration options
