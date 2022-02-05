
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

## install

This is a [scrapy](https://scrapy.org/) project, so it needs to be run with the
`scrapy` command line util. A conda `environment.yml` file is provided with a definition
for the necessary environment to run the scraper.

```console
# create and activate conda environment
conda env create -f environment.yml
conda activate transfermarkt-scraper
```
> :information_source: On Apple silicon chips fallback to rosetta to avoid well-known [pyopenssl issues](https://github.com/pyca/pyopenssl/issues/873) by creating your conda environment as `CONDA_SUBDIR=osx-64 conda env create -f environment.yml`

## run
> :warning: When using this scraper please identify your project accordingly by passing the user agent string using the `USER_AGENT` scrapy setting. For example, `scrapy crawl players -s USER_AGENT=<your user agent> `

```console
# discover confederantions and competitions on separate invokations
scrapy crawl confederations > confederations.json
scrapy crawl competitions -a parents=confederations.json > competitions.json

# you can use intermediate files or pipe crawlers one after the other to traverse the hierarchy 
cat competitions | head -2 \
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

Items are extracted in JSON format with one JSON object per item (confederation, league, club, player or appearance), which gets printed to the `stdout`. Samples of extracted data are provided in the [samples](samples) folder.

Check out [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) to see `transfermarkt-scraper` in action on a real project.

## config
Check [setting.py](tfmkt/settings.py) for a reference of available configuration options

## contribute
Extending existing crawlers in this project in order to scrape additional data or even creating new crawlers is quite straightforward. If you want to contribute with an enhancement to `transfermarkt-scraper` I suggest that you follow a workflow similar to
1. Fork the repository
2. Modify or add new crawlers to `tfmkt/spiders`. [Here is an example PR](https://github.com/dcaribou/transfermarkt-scraper/pull/25/files) that extends the `games` crawler to scrape a few additional fields from Transfermakt games page.
3. Create a PR with your changes and a short description for the enhancement and send it over :rocket:

It is usually also a good idea to have a short discussion about the enhancement beforehand. If you want to propose a change and collect some feeback before you start coding you can do so by creating an issue with your idea in the [Issues](https://github.com/dcaribou/transfermarkt-scraper/issues) section.
