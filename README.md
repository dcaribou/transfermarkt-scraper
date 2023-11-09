
![checks status](https://github.com/dcaribou/transfermarkt-scraper/workflows/Scrapy%20Contracts%20Checks/badge.svg)
![docker build status](https://github.com/dcaribou/transfermarkt-scraper/workflows/Dockerhub%20Image/badge.svg)
# transfermarkt-scraper

A web scraper for collecting data from [Transfermarkt](https://www.transfermarkt.co.uk/) website. It recurses into the Transfermarkt hierarchy to find
[competitions](https://www.transfermarkt.co.uk/wettbewerbe/europa), 
[games](https://www.transfermarkt.co.uk/premier-league/gesamtspielplan/wettbewerb/GB1/saison_id/2020),
[clubs](https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1),
[players](https://www.transfermarkt.co.uk/manchester-city/kader/verein/281/saison_id/2019) and [appearances](https://www.transfermarkt.co.uk/sergio-aguero/leistungsdaten/spieler/26399), and extract them as JSON objects. 

```console
====> Confederations ====> Competitions ====> (Clubs, Games) ====> Players ====> Appearances
```

Each one of these entities can be discovered and refreshed separately by invoking the corresponding crawler.

## Installation

This is a [scrapy](https://scrapy.org/) project, so it needs to be run with the
`scrapy` command line util. This and all other required dependencies can be installed using [poetry](https://python-poetry.org/docs/).

```console
cd transfermarkt-scraper
poetry install
poetry shell
```

## Usage

> :warning: This project will not run without a user agent string being set. This can be done one of two ways:
> - add `ROBOTSTXT_USER_AGENT = <your user agent>` to your tfmkt/settings.py file, or
> - specify the user agent token in the command line request (for example, `scrapy crawl players -s USER_AGENT=<your user agent> `)

These are some usage examples for how the scraper may be run.

```console
# discover confederantions and competitions on separate invokations
scrapy crawl confederations > confederations.json
scrapy crawl competitions -a parents=confederations.json > competitions.json

# you can use intermediate files or pipe crawlers one after the other to traverse the hierarchy 
cat competitions.json | head -2 \
    | scrapy crawl clubs \
    | scrapy crawl players \
    | scrapy crawl appearances
```

Alternatively you can also use [`dcaribou/transfermarkt-scraper`](https://hub.docker.com/repository/docker/dcaribou/transfermarkt-scraper) docker image

```console
docker run \
    -ti -v "$(pwd)"/.:/app \
    dcaribou/transfermarkt-scraper:main \
    scrapy crawl competitions -a parents=samples/confederations.json
```

Items are extracted in JSON format with one JSON object per item (confederation, league, club, player or appearance), which get printed to the `stdout`. Samples of extracted data are provided in the [samples](samples) folder.

Check out [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) to see `transfermarkt-scraper` in action on a real project.

### arguments
- `parents`: Crawler "parents" are either a file or a piped output with the parent entities. For example, `competitions` is parent of `clubs`, which in turn is a parent of `players`.
- `season`: The season that the crawler is to run for. It defaults to the most recent season.

## config
Check [setting.py](tfmkt/settings.py) for a reference of available configuration options

## contribute
Extending existing crawlers in this project in order to scrape additional data or even creating new crawlers is quite straightforward. If you want to contribute with an enhancement to `transfermarkt-scraper` I suggest that you follow a workflow similar to
1. Fork the repository
2. Modify or add new crawlers to `tfmkt/spiders`. [Here is an example PR](https://github.com/dcaribou/transfermarkt-scraper/pull/25/files) that extends the `games` crawler to scrape a few additional fields from Transfermakt games page.
3. Create a PR with your changes and a short description for the enhancement and send it over :rocket:

It is usually also a good idea to have a short discussion about the enhancement beforehand. If you want to propose a change and collect some feeback before you start coding you can do so by creating an issue with your idea in the [Issues](https://github.com/dcaribou/transfermarkt-scraper/issues) section.
