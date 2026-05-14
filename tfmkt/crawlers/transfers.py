import json
import logging
import re
from urllib.parse import urlparse

from crawlee import Request

from tfmkt.common import DEFAULT_BASE_URL, load_parents, create_crawler, check_failures

logger = logging.getLogger(__name__)


async def run(parents_arg=None, season=2024, base_url=None):
    base_url = base_url or DEFAULT_BASE_URL

    crawler, failures = create_crawler()

    parents = load_parents(parents_arg)
    start_requests = []
    for item in parents:
        href = item.get('href')
        if not href:
            continue
        if '/plus/' not in href and '/saison_id/' not in href:
            if '/transfers/' not in href:
                href = href.replace('/startseite/', '/transfers/')
            if '/transfers/' not in href:
                href = href.rstrip('/') + '/transfers'
            # Club pages (/verein/) use /saison_id/YEAR; competition pages use /plus/?saison_id=...
            if '/verein/' in href:
                href = href.rstrip('/') + f'/saison_id/{season}'
            else:
                href = href.rstrip('/') + f'/plus/?saison_id={season}&s_w=&leihe=1&intern=0&intern=1'
        url = base_url + href
        start_requests.append(Request.from_url(url=url, label='parse_transfers', user_data={'source': url, 'parent': item}))

    @crawler.router.handler('parse_transfers')
    async def parse_transfers(context) -> None:
        sel = context.selector

        tables = sel.xpath("//div[contains(@class,'responsive-table')]//table | //table[contains(@class,'items')]")
        if not tables:
            logger.warning('No transfer tables found on %s', context.request.url)
            return

        for tbl in tables:
            # string() captures text from nested elements (e.g. linked club names)
            team_name = tbl.xpath('string(preceding::h2[1])').get()
            if not team_name or not team_name.strip():
                team_name = tbl.xpath('string(preceding::h3[1])').get()
            team_name = team_name.strip() if team_name else ''
            # On single-club pages the preceding h2 is "Arrivals"/"Departures", not a club name
            _tn = team_name.lower()
            if not team_name or any(w in _tn for w in ('arrival', 'departure', 'entrad', 'saíd', 'zugäng', 'abgäng')):
                team_name = sel.xpath('string(//h1)').get('').strip()

            direction = ''
            hdr_texts = tbl.xpath('.//thead//tr//th/text()').getall() or []
            for t in hdr_texts:
                tt = (t or '').strip().lower()
                if tt in ('in', 'ins', 'arrivals', 'arrival') or 'in ' in tt:
                    direction = 'In'
                    break
                if tt in ('out', 'outs', 'departures', 'departure') or 'out ' in tt:
                    direction = 'Out'
                    break
            if not direction:
                # Fallback: some pages label tables with headings rather than header cells
                dir_candidate = tbl.xpath('string(preceding::h3[1])').get() or tbl.xpath('string(preceding::h2[1])').get()
                if dir_candidate:
                    dc = dir_candidate.strip().lower()
                    if 'in' in dc or 'arrival' in dc or 'ins' in dc:
                        direction = 'In'
                    elif 'out' in dc or 'depart' in dc or 'outs' in dc:
                        direction = 'Out'

            rows = tbl.xpath('./tbody/tr') or tbl.xpath('./tr')
            for r in rows:
                if r.xpath('.//th'):
                    continue

                def cell_text(xpath_expr):
                    try:
                        v = r.xpath(xpath_expr).get()
                        return v.strip() if v else ''
                    except Exception:
                        return ''

                player_anchor = r.xpath('.//a[contains(@href, "/spieler/")]')
                player_href = player_anchor.xpath('@href').get()
                if not player_href:
                    continue
                player = player_anchor.xpath('text()').get('').strip()
                player_href = player_href.strip()
                if player_href.startswith('http'):
                    player_href = urlparse(player_href).path

                age = cell_text('.//td[contains(@class,"alter-transfer-cell")]/text()')
                if not age:
                    age = cell_text('./td[@class="zentriert"][1]/text()')

                nationality = r.xpath('.//td[contains(@class,"nat-transfer-cell")]//img/@title').get()
                if not nationality:
                    nationality = cell_text('.//td[contains(@class,"nat-transfer-cell")]/text()')
                if not nationality:
                    nationality = r.xpath('./td[@class="zentriert"][2]//img/@title').get() or ''
                if nationality:
                    nationality = nationality.strip()

                position = cell_text('.//td[contains(@class,"pos-transfer-cell")]/text()')
                if not position:
                    position = cell_text('.//td[contains(@class,"kurzpos-transfer-cell")]/text()')
                if not position:
                    position = r.xpath('.//table[@class="inline-table"]//tr[2]/td/text()').get() or ''

                market_value = cell_text('.//td[contains(@class,"mw-transfer-cell")]/text()')

                from_club = r.xpath('.//td[contains(@class,"no-border-rechts")]//a/text()').get()
                if not from_club:
                    from_club = r.xpath('.//td[contains(@class,"verein-flagge-transfer-cell")]//a/text()').get()
                if not from_club:
                    from_club = r.xpath('./td[5]//a/text()').get()
                if from_club:
                    from_club = from_club.strip()

                # Fee cells can be multi-line: "Loan fee:<br><i class='normaler-text'>€1.50m</i>"
                fee_elem = r.xpath('.//td//a[contains(@href,"jumplist")]')
                if fee_elem:
                    fee = fee_elem.xpath('string(.)').get()
                else:
                    fee = r.xpath('string(.//td[last()])').get()
                if fee:
                    fee = re.sub(r"\s+", " ", fee).strip()
                    fee = re.sub(r":(?=[€$£\d])", ": ", fee)
                    fee = re.sub(r"(?i)(loan)(?=\s*\d{1,2}/\d{1,2}/\d{2,4})", r"\1 ", fee)
                else:
                    fee = ''

                item = {
                    'type': 'transfer',
                    'club': team_name or '',
                    'direction': direction or '',
                    'player': player or '',
                    'player_href': player_href or '',
                    'age': age or '',
                    'nationality': nationality or '',
                    'position': position or '',
                    'market_value': market_value or '',
                    'origin_club': from_club or '',
                    'fee': fee or '',
                }
                parent = context.request.user_data.get('parent') if hasattr(context.request, 'user_data') else None
                if parent:
                    item['parent'] = parent
                item['source'] = context.request.url

                print(json.dumps(item), flush=True)

    await crawler.run(start_requests)
    check_failures(failures)
