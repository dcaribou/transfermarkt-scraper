from tfmkt.spiders.common_comp_club import BaseSpider
from urllib.parse import unquote, urlparse
import re

class ClubsSpider(BaseSpider):
    name = 'clubs'

    def parse(self, response, parent):
        """
        Parse competition page. From this page we collect all competition's
        team URLs from all 'responsive-table' blocks that appear to contain club info.
        
        @url https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1
        @returns requests
        @cb_kwargs {"parent": "dummy"}
        @scrapes type href parent
        """
        def is_teams_table(table):
            # Check the table headers; if any header contains the word "club" (case insensitive), we consider it a teams table.
            headers = [h.strip().lower() for h in table.css('th::text').getall() if h]
            return any("club" in hdr for hdr in headers)

        def extract_team_href(row):
            # We assume that the second <td> contains the team link.
            tds = row.css('td')
            if len(tds) >= 2:
                return tds[1].css('a::attr(href)').get()
            return None

        page_tables = response.css('div.responsive-table')
        teams_tables = [table for table in page_tables if is_teams_table(table)]
        self.logger.info("Found %d responsive-table(s) on %s", len(teams_tables), response.url)

        # Loop over each teams table (if more than one exists)
        for table in teams_tables:
            for row in table.css('tbody tr'):
                href = extract_team_href(row)
                if not href:
                    continue

                # DO NOT strip out the season id. Use the link as provided (e.g. it includes /saison_id/2024)
                # This preserves the correct season.
                club_href = href  

                cb_kwargs = {
                    'base': {
                        'type': 'club',
                        'href': club_href,
                        'parent': parent  # parent is the competition item (which should already have correct competition_code, etc.)
                    }
                }
                squad_url = club_href.replace("/startseite/", "/kader/") + "/plus/1"
                yield response.follow(squad_url, self.parse_details, cb_kwargs=cb_kwargs)

    def parse_details(self, response, base):
        """
        Extract club details from the club page.
        
        @url https://www.transfermarkt.co.uk/fc-bayern-munchen/startseite/verein/27
        @returns items 1 1
        @cb_kwargs {"base": {"href": "some_href/path/to/code", "type": "club", "parent": {}}}
        @scrapes href type parent
        """
        safe = self.safe_strip
        attributes = {}

        # Extract market value from the "dataMarktwert" section
        attributes['total_market_value'] = response.css('div.dataMarktwert a::text').get()

        # Extract "Squad size" and "Average age" from the data content section
        attributes['squad_size'] = self.safe_strip(
            response.xpath("//li[contains(text(),'Squad size:')]/span/text()").get()
        )
        attributes['average_age'] = self.safe_strip(
            response.xpath("//li[contains(text(),'Average age:')]/span/text()").get()
        )
        
        # Extract foreigners information
        foreigners_li = response.xpath("//li[contains(text(),'Foreigners:')]")
        if foreigners_li:
            attributes['foreigners_number'] = self.safe_strip(foreigners_li[0].xpath("span/a/text()").get())
            attributes['foreigners_percentage'] = self.safe_strip(
                foreigners_li[0].xpath("span/span/text()").get()
            )
        else:
            attributes['foreigners_number'] = None
            attributes['foreigners_percentage'] = None

        # Extract national team players count
        attributes['national_team_players'] = self.safe_strip(
            response.xpath("//li[contains(text(),'National team players:')]/span/a/text()").get()
        )

        # Extract stadium name and seating capacity
        stadium_li = response.xpath("//li[contains(text(),'Stadium:')]")
        if stadium_li:
            attributes['stadium_name'] = self.safe_strip(stadium_li[0].xpath("span/a/text()").get())
            attributes['stadium_seats'] = self.safe_strip(stadium_li[0].xpath("span/span/text()").get())
        else:
            attributes['stadium_name'] = None
            attributes['stadium_seats'] = None

        # Extract net transfer record and coach name
        attributes['net_transfer_record'] = self.safe_strip(
            response.xpath("//li[contains(text(),'Current transfer record:')]/span/span/a/text()").get()
        )
        coach_name = response.xpath('//div[contains(@data-viewport, "Mitarbeiter")]//div[@class="container-hauptinfo"]/a/text()').get()
        attributes['coach_name'] = coach_name.strip() if coach_name else None

        # Extract a short code from the club URL and the club name
        attributes['code'] = unquote(urlparse(base["href"]).path.split("/")[1])
        name_val = response.xpath("//span[@itemprop='legalName']/text()").get() or \
                   response.xpath('//h1[contains(@class,"data-header__headline-wrapper")]/text()').get()
        attributes['name'] = self.safe_strip(name_val)

        for key, value in attributes.items():
            if isinstance(value, str):
                attributes[key] = value.strip()
        
        # --- after collecting attributes ------------------------------
    
        seen_player_ids: set[int] = set()          # <- de-duplicate whole table

        def parse_player_row(tr):
            link = tr.css("td.posrela a::attr(href)").get()
            if not link:                       # header / empty spacer row
                return None

            m_id = re.search(r"/spieler/(\d+)", link)
            if not m_id:
                return None
            pid = int(m_id.group(1))

            if pid in seen_player_ids:         # icon-row duplicate → skip
                return None
            seen_player_ids.add(pid)

            tds = tr.css("td")                 # list of *all* cells
            # ------------------------------------------------------------------
            # fixed columns
            # ------------------------------------------------------------------
            number   = safe(tds[0].css("div.rn_nummer::text").get())
            name     = safe(tr.css("td.posrela a::text").get())
            position = safe(tr.css("td.posrela tr:nth-child(2) td::text").get())

            # ------------------------------------------------------------------
            # variable-offset columns
            # after the posrela cell there are either
            #   dob-age | [icon?]nat | height | foot | joined | from | contract | value
            # so:  len(tds) == 10  …icon missing
            #      len(tds) == 11  …icon present  (extra td right after nat flags)
            # We calculate the offset once and index from the *end* for stability.
            # ------------------------------------------------------------------
            
            self.logger.debug("PAY ATTENTION TO THIS: %s", len(tds))        

            dob_age_td       = tds[-8]                          # same in both cases
            nat_td           = tds[-7]                          # flags td
            height_td        = tds[-6]
            foot_td          = tds[-5]
            joined_td        = tds[-4]
            signed_from_td   = tds[-3]
            contract_td      = tds[-2]
            value_td         = tds[-1]

            dob_age = safe(dob_age_td.xpath("normalize-space()").get())
            dob, age = None, None
            if dob_age:
                dob, _, rest = dob_age.partition("(")
                dob = safe(dob)
                age = int(rest.rstrip(")")) if rest.rstrip(")").isdigit() else None

            nat = ", ".join(
                safe(img.attrib.get("title"))
                for img in nat_td.css("img[title]")
                if safe(img.attrib.get("title"))
            ) or None

            return {
                "player_id"        : pid,
                "href"             : link,
                "number"           : None if number in {"", "-"} else number,
                "name"             : name,
                "position"         : position,
                "date_of_birth"    : dob,
                "age"              : age,
                "nationality"      : nat,
                "height"           : safe(height_td.xpath("text()").get()),
                "foot"             : safe(foot_td.xpath("text()").get()),
                "joined"           : safe(joined_td.xpath("text()").get()),
                "signed_from_href" : signed_from_td.css("a::attr(href)").get(),
                "signed_from_name" : safe(signed_from_td.css("a::attr(title)").get()),
                "contract_expires" : safe(contract_td.xpath("text()").get()),
                "market_value"     : safe(value_td.css("a::text").get()),
            }

        # ──────────────────────────────────────────────────────────────
        # collect the rows (inside parse_details, replacing previous loop)
        # ──────────────────────────────────────────────────────────────
        players = [
            row for tr in response.css("div.responsive-table table.items tbody tr")
            if (row := parse_player_row(tr))
        ]

        club_item = {**base, **attributes, "players": players}
        self.logger.debug("📦 %s", club_item)
        yield club_item