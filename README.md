# tfmkt-stats
Collects player stats from [Transfermarkt](https://www.transfermarkt.co.uk/) site.

This is a [`scrapy`](https://scrapy.org/) project, so it can be run with the
`scrapy` command line util with `scrapy crawl auto`.

Load the data into your favorite [target](https://www.singer.io/#targets) with
[Singer.io](https://www.singer.io/)

```console
scrapy crawl auto | jq --compact-output '{type: "RECORD", stream: "appearances", record: .}' | [ target-postgres | target-s3 | target-gsheets | target-csv ]
```

## Formatting Output
Use [jq](https://stedolan.github.io/jq/) to format output JSON for your use case.

### Flatten `stats`
```console
scrapy crawl auto | jq --compact-output '. as $in | .stats[] as $appearance | $in | del(.stats) | . + $appearance'
```
### Rename some field
```console
scrapy crawl auto | jq --compact-output '. + {league: .domestic_competition} | del(.domestic_competition)'
```
### Follow [Singer.io](https://www.singer.io/)
```console
scrapy crawl auto | jq --compact-output '{type: "RECORD", stream: "appearances", record: .}'
```
