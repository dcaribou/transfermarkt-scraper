# Uncaptured Fields Analysis

Analysis of transfermarkt pages currently visited by the scraper, comparing fields being
extracted vs fields available on each page. This document serves as input for planning a
general enhancement to maximize data extraction from pages we already hit.

---

## 1. Competition Pages

**Pages visited:**
- Confederation listing: `/wettbewerbe/{confederation}` (paginated)
- Country competition listing: `/wettbewerbe/national/wettbewerbe/{country_id}`

### Currently captured
| Field | Source |
|---|---|
| `country_id` | confederation page row |
| `country_name` | confederation page row |
| `country_code` | confederation page row |
| `competition_type` | country page (first_tier, domestic_cup, etc.) |
| `href` | country page |
| `total_clubs` | confederation page row |
| `total_players` | confederation page row |
| `average_age` | confederation page row |
| `foreigner_percentage` | confederation page row |
| `total_value` | confederation page row |

### Uncaptured fields available

| Field | Where | Notes |
|---|---|---|
| `competition_name` | confederation page & country page | The name of the league/cup (e.g. "Premier League"). Currently only the href is stored |
| `competition_code` | extractable from `href` | The short code (e.g. "GB1", "CL"). Derivable from href but not stored explicitly |
| `competition_image_url` | country competition list | League/competition logo URL |
| `country_flag_url` | confederation page row | Flag image URL for the country |
| `current_champion` | country page | Reigning champion club name and href (shown on the country's competition page) |
| `record_champion` | country page | Club with most titles |
| `most_valuable_player` | confederation page row column | Link to the most valuable player |
| `tier_level` | country competition list | Numeric tier (1st, 2nd, 3rd) as an integer rather than a string label |

**Impact: 5-8 new fields per competition item.**

---

## 2. Club Pages

**Pages visited:**
- League overview (club listing): `/{league}/startseite/wettbewerb/{code}/plus/0?saison_id={season}`
- Individual club detail: `/{club}/startseite/verein/{id}/saison_id/{season}`

### Currently captured
| Field | Source |
|---|---|
| `name` | club detail page |
| `code` | derived from href |
| `total_market_value` | club detail page |
| `squad_size` | club detail page |
| `average_age` | club detail page |
| `foreigners_number` | club detail page |
| `foreigners_percentage` | club detail page |
| `national_team_players` | club detail page |
| `stadium_name` | club detail page |
| `stadium_seats` | club detail page |
| `net_transfer_record` | club detail page |
| `coach_name` | club detail page |

### Uncaptured fields available

| Field | Where | Notes |
|---|---|---|
| `club_image_url` | club detail page header | Club crest/logo image |
| `official_name` | club detail page | The legal/official name of the club (shown in header with `itemprop='legalName'`; already partially used for `name` fallback but not stored separately) |
| `founded_on` | club detail page sidebar ("Founded:") | Year the club was founded |
| `address_line_1` | club detail page sidebar ("Address:") | Street address |
| `address_line_2` | club detail page sidebar | City/ZIP |
| `address_line_3` | club detail page sidebar | Country |
| `telephone` | club detail page sidebar ("Tel:") | Phone number |
| `fax` | club detail page sidebar ("Fax:") | Fax number |
| `website` | club detail page sidebar ("Website:") | Official website URL |
| `club_colors` | club detail page sidebar | Official club colors |
| `members` | club detail page sidebar ("Members:") | Number of club members |
| `other_sports` | club detail page sidebar | Other sports sections the club has |
| `coach_href` | club detail page | Coach profile link (currently only name is captured) |
| `coach_image_url` | club detail page | Coach photo |
| `league_position` | club detail page | Current league standing/position |
| `historical_crests` | club detail page | Previous club logos/crests |
| `confederation` | club detail page | UEFA, CONMEBOL, etc. |
| `average_market_value` | league overview page | Per-player average market value |

**Impact: 13-18 new fields per club item.**

---

## 3. Player Profile Pages

**Pages visited:**
- Club squad page (listing): `/{club}/kader/verein/{id}/saison_id/{season}`
- Individual player profile: `/{player}/profil/spieler/{id}`

### Currently captured
| Field | Source |
|---|---|
| `name` | profile page |
| `last_name` | profile page |
| `number` | profile page header |
| `code` | derived from href |
| `name_in_home_country` | profile page |
| `date_of_birth` | profile page |
| `age` | profile page |
| `place_of_birth` (city + country) | profile page |
| `height` | profile page |
| `citizenship` | profile page (single) |
| `position` | profile page |
| `foot` | profile page |
| `player_agent` (name + href) | profile page |
| `image_url` | profile page |
| `current_club` (href) | profile page |
| `joined` | profile page |
| `contract_expires` | profile page |
| `day_of_last_contract_extension` | profile page |
| `outfitter` | profile page |
| `current_market_value` | profile page |
| `highest_market_value` | profile page |
| `social_media` | profile page |
| `market_value_history` | profile page (JS) |

### Uncaptured fields available

| Field | Where | Notes |
|---|---|---|
| `full_name` | profile page ("Full name:" row) | Complete legal name, distinct from `name_in_home_country` |
| `description` | profile page header | Brief description/tagline under player name |
| `second_citizenship` | profile page ("Citizenship:" row) | Multiple citizenship flags are displayed; only first is captured |
| `position_main` | profile page | Main position (e.g. "Centre-Forward") |
| `position_other` | profile page | Sub-position(s) (e.g. "Left Winger, Right Winger"). Available on the page but not extracted |
| `shirt_number` | profile page header | Already extracted as `number` but only from page header; also on squad list |
| `current_club_name` | profile page | Club name text (currently only href is captured) |
| `current_club_id` | derivable from club href | Numeric club ID |
| `contract_option` | profile page | Contract option details (e.g. "Option for 1 year") |
| `last_club_name` | profile page | Previous club name |
| `last_club_href` | profile page | Previous club link |
| `most_games_for_club` | profile page | Club where the player has most appearances |
| `is_retired` | profile page | Whether the player is retired |
| `retired_since` | profile page | Date of retirement |
| `date_of_death` | profile page | For deceased players |
| `market_value_last_change_date` | profile page | Date when market value was last updated |
| `relatives` | profile page | Related players/family in football (name + href + relation type) |
| `caps_and_goals` | profile page sidebar | National team appearances and goals summary |
| `transfer_history` | profile page (transfer section) | Complete list of transfers with fees, dates, from/to clubs. Available on the profile page in a dedicated section |
| `injury_history` | profile page (injury section) | Past injuries with dates, days missed, games missed |
| `achievements` | profile page | Trophies and titles won |

**Impact: 15-21 new fields per player item.**

---

## 4. Player Appearances / Stats Pages

**Pages visited:**
- Player profile page (to find stats link): `/{player}/profil/spieler/{id}`
- Full stats page: `/{player}/leistungsdaten/spieler/{id}/plus/0?saison={season}`

### Currently captured
| Field | Source |
|---|---|
| `competition_code` | stats page |
| `matchday` | stats page table |
| `date` | stats page table |
| `venue` (H/A) | stats page table |
| `for` (club href) | stats page table |
| `opponent` (club href) | stats page table |
| `result` (game href) | stats page table |
| `pos` | stats page table |
| `goals` | stats page table |
| `assists` | stats page table |
| `yellow_cards` | stats page table |
| `second_yellow_cards` | stats page table |
| `red_cards` | stats page table |
| `minutes_played` | stats page table |

### Uncaptured fields available

| Field | Where | Notes |
|---|---|---|
| `own_goals` | stats page table | Own goals column (shown as separate column or icon in some views) |
| `substituted_on` | stats page table | Minute of substitution in |
| `substituted_off` | stats page table | Minute of substitution off |
| `penalty_goals` | stats page table | Goals scored from penalties |
| `goals_conceded` | stats page table (GK) | Goals conceded (goalkeeper-specific column) |
| `clean_sheets` | stats page table (GK) | Clean sheets (goalkeeper-specific column) |
| `competition_name` | stats page section headers | Full competition name (e.g. "Premier League"). Currently only `competition_code` is stored |
| `season_totals` | stats page footer rows | Per-competition season summary row with totals for goals, assists, cards, minutes |
| `not_in_squad` | stats page table | Indicator when player was registered but not in matchday squad |
| `on_the_bench` | stats page table | Indicator when player was on the bench but didn't play |
| `suspended` | stats page table | Indicator when player was suspended |
| `injured` | stats page table | Indicator when player was injured |
| `market_value_at_time` | stats page column | Market value at that point in time (shown in some views) |

**Impact: 7-13 new fields per appearance item.**

---

## 5. Game Report Pages

**Pages visited:**
- Competition schedule: `/{competition}/spieltag/...` (to extract game URLs)
- Individual game report: `/{home}_vs_{away}/index/spielbericht/{game_id}`

### Currently captured
| Field | Source |
|---|---|
| `game_id` | derived from href |
| `home_club` (href) | game report |
| `away_club` (href) | game report |
| `home_club_position` | game report |
| `away_club_position` | game report |
| `result` | game report |
| `matchday` | game report |
| `date` | game report |
| `stadium` | game report |
| `attendance` | game report |
| `referee` | game report |
| `home_manager` (name) | game report |
| `away_manager` (name) | game report |
| `events[]` (goals, subs, cards, shootout) | game report |

### Uncaptured fields available

| Field | Where | Notes |
|---|---|---|
| `home_club_name` | game report header | Club name text (currently only href is stored) |
| `away_club_name` | game report header | Club name text |
| `home_club_image_url` | game report header | Club crest image |
| `away_club_image_url` | game report header | Club crest image |
| `home_manager_href` | game report | Manager profile link (currently only name is captured) |
| `away_manager_href` | game report | Manager profile link |
| `referee_href` | game report | Referee profile link (currently only name is captured via @title) |
| `half_time_result` | game report | Half-time score (shown in result section) |
| `extra_time_result` | game report | Extra time score when applicable |
| `penalty_result` | game report | Penalty shootout score when applicable |
| `kick_off_time` | game report | Match start time |
| `matchday_number` | game report | Numeric matchday (currently stored as text like "13. Matchday") |
| `season` | game report | Season year |
| `home_formation` | game report | Tactical formation used (e.g. "4-3-3") |
| `away_formation` | game report | Tactical formation used |
| `home_club_market_value` | game report sidebar | Squad market value shown on match page |
| `away_club_market_value` | game report sidebar | Squad market value shown on match page |
| `missed_penalties` | game report events | Missed penalties during the game (separate event section) |
| `event[].player_name` | game report events | Player name text for each event (currently only href is stored) |

**Impact: 12-19 new fields per game item.**

---

## 6. Game Lineup Pages

**Pages visited:**
- Game report page (to extract lineup URL): `/{match}/index/spielbericht/{game_id}`
- Lineup page: `/{match}/aufstellung/spielbericht/{game_id}`

### Currently captured
| Field | Source |
|---|---|
| `game_id` | from parent |
| `home_club.href` | from parent |
| `away_club.href` | from parent |
| `home_club.formation` | lineup page |
| `away_club.formation` | lineup page |
| `home_club.starting_lineup[]` | lineup page (number, href, name, team_captain, position) |
| `home_club.substitutes[]` | lineup page (number, href, name, team_captain, position) |
| `away_club.starting_lineup[]` | lineup page (same fields) |
| `away_club.substitutes[]` | lineup page (same fields) |

### Uncaptured fields available

| Field | Where | Notes |
|---|---|---|
| `player.age` | lineup page table | Player age at time of match |
| `player.nationality` | lineup page table | Player nationality flag(s) |
| `player.market_value` | lineup page table | Player market value at time of match |
| `player.image_url` | lineup page player row | Player photo thumbnail |
| `player.minutes_played` | lineup page | Minutes played by each player |
| `player.substituted_for` | lineup page substitutes section | Which player they replaced (for subs who came on) |
| `player.substitution_minute` | lineup page | Minute of substitution |
| `manager.name` | lineup page | Manager name for each team |
| `manager.href` | lineup page | Manager profile link |
| `not_in_squad[]` | lineup page | Players not included in the matchday squad |
| `absent_players[]` | lineup page | Players marked as absent (injured, suspended, etc.) with reason |

**Impact: 8-11 new fields per lineup entry / per player.**

---

## Summary

| Page Type | Currently Captured | Available to Add | Effort |
|---|---|---|---|
| **Competitions** | 10 fields | 5-8 fields | Low -- same pages, simple selectors |
| **Clubs** | 12 fields | 13-18 fields | Medium -- some fields in sidebar require new selectors |
| **Players** | 23 fields | 15-21 fields | High -- some fields (transfers, injuries, achievements) are in separate page sections |
| **Appearances** | 14 fields | 7-13 fields | Medium -- GK-specific columns, status indicators |
| **Games** | 14 fields | 12-19 fields | Medium -- half-time score, formations, missed penalties |
| **Game Lineups** | 9 fields (+ 5/player) | 8-11 fields | Medium -- player-level enrichment from lineup table |
| **Total** | **~82 fields** | **~60-90 new fields** | |

### Recommended priority order

1. **Players** -- Highest value-add. Transfer history, second citizenship, sub-positions, and injury history are heavily used in football analytics.
2. **Clubs** -- Club founding date, colors, address, and website are stable metadata that rarely changes. Logo URL is useful for any frontend.
3. **Games** -- Half-time result, formations, and kick-off time add match context with minimal extra parsing.
4. **Competitions** -- Competition name is a glaring omission; low effort to add.
5. **Appearances** -- GK-specific stats and substitution details fill important gaps.
6. **Game Lineups** -- Player-level enrichment (age, nationality, market value at match time) is high-value but requires careful parsing.
