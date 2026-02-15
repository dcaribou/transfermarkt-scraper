import json
import re

from crawlee import Request
from crawlee.crawlers import ParselCrawler

from tfmkt.common import DEFAULT_BASE_URL, load_parents, build_initial_requests, safe_strip
from tfmkt.utils import background_position_in_px_to_minute


def extract_game_events(selector, event_type):
    event_elements = selector.xpath(
        f"//div[./h2/@class = 'content-box-headline' and normalize-space(./h2/text()) = "
        f"'{'Penalty shoot-out' if event_type == 'Shootout' else event_type}']"
        f"//div[@class='sb-aktion']"
    )

    events = []
    for e in event_elements:
        event = {}
        event["type"] = event_type
        if event_type == "Shootout":
            event["minute"] = -1
            extra_minute_text = ''
        else:
            background_position_match = re.match(
                "background-position: ([-+]?[0-9]+)px ([-+]?[0-9]+)px;",
                e.xpath("./div[1]/span[@class='sb-sprite-uhr-klein']/@style").get()
            )
            event["minute"] = background_position_in_px_to_minute(
                int(background_position_match.group(1)),
                int(background_position_match.group(2)),
            )
            extra_minute_text = safe_strip(
                e.xpath("./div[1]/span[@class='sb-sprite-uhr-klein']/text()").get()
            )
        if len(extra_minute_text) <= 1:
            extra_minute = None
        else:
            extra_minute = int(extra_minute_text)

        event["extra"] = extra_minute
        event["player"] = {
            "href": e.xpath("./div[@class = 'sb-aktion-spielerbild']/a/@href").get()
        }
        event["club"] = {
            "name": e.xpath("./div[@class = 'sb-aktion-wappen']/a/@title").get(),
            "href": e.xpath("./div[@class = 'sb-aktion-wappen']/a/@href").get()
        }

        action_element = e.xpath("./div[@class = 'sb-aktion-aktion']")
        event["action"] = {
            "result": safe_strip(
                e.xpath("./div[@class = 'sb-aktion-spielstand']/b/text()").get()
            ),
            "description": safe_strip(
                (" ".join([s.strip() for s in action_element.xpath("./text()").getall()])).strip()
                or (" ".join(action_element.xpath(
                    ".//span[@class = 'sb-aktion-wechsel-aus']/span/text()"
                ).getall())).strip()
            ),
            "player_in": {
                "href": action_element.xpath(".//div/a/@href").get()
            },
            "player_assist": {
                "href": action_element.xpath("./a/@href").getall()[1]
                if len(action_element.xpath("./a/@href").getall()) > 1 else None
            }
        }
        events.append(event)

    return events


async def run(parents_arg=None, season=2024, base_url=None):
    base_url = base_url or DEFAULT_BASE_URL
    parents = load_parents(parents_arg)
    requests = build_initial_requests(parents, season, base_url, label='parse', spider_name='games')

    crawler = ParselCrawler()

    @crawler.router.handler('parse')
    async def parse(context) -> None:
        parent = context.request.user_data['parent']
        sel = context.selector

        cb_data = {'parent': parent}

        footer_links = sel.css('div.footer-links')
        for footer_link in footer_links:
            text = footer_link.xpath('a//text()').get().strip()
            if text in ["All fixtures & results", "All games"]:
                next_url = footer_link.xpath('a/@href').get()
                await context.add_requests([
                    Request.from_url(
                        url=base_url + next_url,
                        label='extract_game_urls',
                        user_data={'base': cb_data},
                    )
                ])
                return

    @crawler.router.handler('extract_game_urls')
    async def extract_game_urls_handler(context) -> None:
        base = context.request.user_data['base']
        sel = context.selector

        game_links = sel.css('a.ergebnis-link')
        new_requests = []
        for game_link in game_links:
            href = game_link.xpath('@href').get()
            cb_data = {
                'parent': base['parent'],
                'href': href,
            }
            new_requests.append(
                Request.from_url(
                    url=base_url + href,
                    label='parse_game',
                    user_data={'base': cb_data},
                )
            )

        if new_requests:
            await context.add_requests(new_requests)

    @crawler.router.handler('parse_game')
    async def parse_game(context) -> None:
        base = context.request.user_data['base']
        sel = context.selector

        game_id = int(base['href'].split('/')[-1])

        game_box = sel.css('div.box-content')

        home_club_box = game_box.css('div.sb-heim')
        away_club_box = game_box.css('div.sb-gast')

        home_club_href = home_club_box.css('a::attr(href)').get()
        home_club_name = safe_strip(
            home_club_box.xpath('.//a/@title').get()
        ) or safe_strip(
            home_club_box.xpath('.//a/img/@alt').get()
        )
        away_club_href = away_club_box.css('a::attr(href)').get()
        away_club_name = safe_strip(
            away_club_box.xpath('.//a/@title').get()
        ) or safe_strip(
            away_club_box.xpath('.//a/img/@alt').get()
        )

        home_club_position = home_club_box[0].xpath('p/text()').get()
        away_club_position = away_club_box[0].xpath('p/text()').get()

        datetime_box = game_box.css('div.sb-spieldaten')[0]

        text_elements = [
            element for element in datetime_box.xpath('p//text()')
            if len(safe_strip(element.get())) > 0
        ]

        matchday = safe_strip(text_elements[0].get()).split("  ")[0]
        date = safe_strip(datetime_box.xpath('p/a[contains(@href, "datum")]/text()').get())

        venue_box = game_box.css('p.sb-zusatzinfos')

        stadium = safe_strip(venue_box.xpath('node()')[1].xpath('a/text()').get())
        attendance = safe_strip(venue_box.xpath('node()')[1].xpath('strong/text()').get())
        referee = safe_strip(venue_box.xpath('a[contains(@href, "schiedsrichter")]/@title').get())
        referee_href = venue_box.xpath('a[contains(@href, "schiedsrichter")]/@href').get()

        result_box = game_box.css('div.ergebnis-wrap')
        result = safe_strip(result_box.css('div.sb-endstand::text').get())
        half_time_score = safe_strip(result_box.css('div.sb-halbzeit::text').get())

        # Kickoff time - search for time pattern in the date/time area
        kickoff_time = None
        for el in text_elements:
            text = safe_strip(el.get())
            if text and re.match(r'\d{1,2}:\d{2}', text):
                kickoff_time = text
                break

        manager_names = sel.xpath(
            "//tr[(contains(td/b/text(),'Manager')) or (contains(td/div/text(),'Manager'))]/td[2]/a/text()"
        ).getall()
        manager_hrefs = sel.xpath(
            "//tr[(contains(td/b/text(),'Manager')) or (contains(td/div/text(),'Manager'))]/td[2]/a/@href"
        ).getall()

        game_events = (
            extract_game_events(sel, event_type="Goals")
            + extract_game_events(sel, event_type="Substitutions")
            + extract_game_events(sel, event_type="Cards")
            + extract_game_events(sel, event_type="Shootout")
        )

        item = {
            **base,
            'type': 'game',
            'game_id': game_id,
            'home_club': {
                'type': 'club',
                'href': home_club_href,
            },
            'home_club_name': home_club_name,
            'home_club_position': home_club_position,
            'away_club': {
                'type': 'club',
                'href': away_club_href,
            },
            'away_club_name': away_club_name,
            'away_club_position': away_club_position,
            'result': result,
            'half_time_score': half_time_score,
            'matchday': matchday,
            'date': date,
            'kickoff_time': kickoff_time,
            'stadium': stadium,
            'attendance': attendance,
            'referee': referee,
            'referee_href': referee_href,
            'events': game_events,
        }

        if len(manager_names) == 2:
            home_manager_name, away_manager_name = manager_names
            home_manager_href = manager_hrefs[0] if len(manager_hrefs) > 0 else None
            away_manager_href = manager_hrefs[1] if len(manager_hrefs) > 1 else None
            item["home_manager"] = {'name': home_manager_name, 'href': home_manager_href}
            item["away_manager"] = {'name': away_manager_name, 'href': away_manager_href}

        print(json.dumps(item), flush=True)

    await crawler.run(requests)
