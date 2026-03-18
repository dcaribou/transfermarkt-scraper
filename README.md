
![checks status](https://github.com/dcaribou/transfermarkt-scraper/workflows/Build%20Checks/badge.svg)
![docker build status](https://github.com/dcaribou/transfermarkt-scraper/workflows/Dockerhub%20Image/badge.svg)

# transfermarkt-scraper

A web scraper for collecting data from [Transfermarkt](https://www.transfermarkt.co.uk/) website. It recurses into the Transfermarkt hierarchy to find
[competitions](https://www.transfermarkt.co.uk/wettbewerbe/europa),
[games](https://www.transfermarkt.co.uk/premier-league/gesamtspielplan/wettbewerb/GB1/saison_id/2020),
[clubs](https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1),
[players](https://www.transfermarkt.co.uk/manchester-city/kader/verein/281/saison_id/2019),
[appearances](https://www.transfermarkt.co.uk/sergio-aguero/leistungsdaten/spieler/26399),
[national teams](https://www.transfermarkt.co.uk/england/startseite/verein/3299) and their competitions, and extract them as JSON objects.

The scraper follows two parallel hierarchies:

```console
# Club football
Confederations ====> Competitions ====> Clubs ====> Players ====> Appearances
                                    ====> Games ====> Game Lineups

# International football
Confederations ====> Countries ====> National Teams ====> Players ====> Appearances
               ====> Competitions (national team competitions: World Cup, Euros, etc.)
```

Each one of these entities can be discovered and refreshed separately by invoking the corresponding crawler.

## Installation
> [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/dcaribou/transfermarkt-scraper/tree/main?quickstart=1)

This project uses [Crawlee for Python](https://crawlee.dev/python/) and can be run with the CLI entry point. All dependencies can be installed using [poetry](https://python-poetry.org/docs/).

```console
cd transfermarkt-scraper
poetry install
poetry shell
```

## Usage

These are some usage examples for how the scraper may be run.

```console
# discover confederations and competitions on separate invocations
python -m tfmkt confederations > confederations.json
python -m tfmkt competitions -p confederations.json > competitions.json

# you can use intermediate files or pipe crawlers one after the other to traverse the hierarchy
cat competitions.json | head -2 \
    | python -m tfmkt clubs \
    | python -m tfmkt players \
    | python -m tfmkt appearances

# scrape national team competitions (World Cup, Euros, Nations League, etc.)
# these are emitted alongside domestic competitions when running the competitions crawler
python -m tfmkt confederations \
    | python -m tfmkt competitions \
    | grep -v '"country_name"' > national_team_competitions.json

# scrape national team squads
python -m tfmkt confederations \
    | python -m tfmkt countries \
    | python -m tfmkt national_teams > national_teams.json

# scrape players from a national team squad
cat national_teams.json | head -1 | python -m tfmkt players
```

Alternatively you can also use [`dcaribou/transfermarkt-scraper`](https://hub.docker.com/repository/docker/dcaribou/transfermarkt-scraper) docker image

```console
docker run \
    -ti -v "$(pwd)"/.:/app \
    dcaribou/transfermarkt-scraper:main \
    python -m tfmkt competitions -p samples/confederations.json
```

Items are extracted in JSON format with one JSON object per item, which get printed to the `stdout`. Samples of extracted data are provided in the [samples](samples) folder.

### Crawlers

| Crawler | Input | Output | Notes |
|---|---|---|---|
| `confederations` | — | Confederation | 5 items: Europa, América, África, Asia, FIFA |
| `competitions` | Confederation | Competition | Domestic + national team competitions per confederation |
| `countries` | Confederation | Country | One item per country (league-bearing nations) |
| `clubs` | Competition (`first_tier`) | Club | Club squads with market value, coach, stadium |
| `national_teams` | Country | National Team | Senior national team per country |
| `players` | Club or National Team | Player | Full player profile including market value history |
| `appearances` | Player | Appearance | Per-match stats for every game played |
| `games` | Competition | Game | Match result, events, managers |
| `game_lineups` | Game | Game Lineups | Starting XI, substitutes, formation |

Check out [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) to see `transfermarkt-scraper` in action on a real project.

### arguments
- `-p` / `--parents`: Crawler "parents" are either a file or a piped output with the parent entities. For example, `competitions` is parent of `clubs`, which in turn is a parent of `players`.
- `-s` / `--season`: The season that the crawler is to run for. It defaults to the most recent season.
- `--base-url`: Override the base Transfermarkt URL.

## contribute
Extending existing crawlers in this project in order to scrape additional data or even creating new crawlers is quite straightforward. If you want to contribute with an enhancement to `transfermarkt-scraper` I suggest that you follow a workflow similar to
1. Fork the repository
2. Modify or add new crawlers to `tfmkt/crawlers`. [Here is an example PR](https://github.com/dcaribou/transfermarkt-scraper/pull/25/files) that extends the `games` crawler to scrape a few additional fields from Transfermakt games page.
3. Create a PR with your changes and a short description for the enhancement and send it over :rocket:

It is usually also a good idea to have a short discussion about the enhancement beforehand. If you want to propose a change and collect some feeback before you start coding you can do so by creating an issue with your idea in the [Issues](https://github.com/dcaribou/transfermarkt-scraper/issues) section.
