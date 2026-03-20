"""Integration tests for all crawlers.

These tests hit the live Transfermarkt site. Each test uses the smallest
possible input to minimize the number of HTTP requests.

Run all:     pytest tests/test_crawlers.py -v
Run one:     pytest tests/test_crawlers.py::test_confederations -v
"""

from tests.conftest import run_crawler


# ---------------------------------------------------------------------------
# 1. Confederations (0 HTTP requests — static output)
# ---------------------------------------------------------------------------

def test_confederations():
    items = run_crawler("confederations")
    assert len(items) == 5
    for item in items:
        assert item["type"] == "confederation"
        assert item["href"].startswith("/wettbewerbe/")
    hrefs = [item["href"] for item in items]
    assert "/wettbewerbe/fifa" in hrefs


# ---------------------------------------------------------------------------
# 2. Competitions (~14 requests — 1 small confederation)
# ---------------------------------------------------------------------------

def test_competitions(tmp_path):
    """Feed a single confederation (afrika, 1 page) to minimize requests."""
    items = run_crawler(
        "competitions",
        parents_data={"type": "confederation", "href": "/wettbewerbe/afrika"},
        tmp_path=tmp_path,
    )
    assert len(items) > 0
    for item in items:
        assert item["type"] == "competition"
        assert "href" in item
        assert "competition_type" in item
        assert "competition_name" in item

    # Domestic competitions have country data and market value
    domestic = [i for i in items if "country_name" in i]
    assert len(domestic) > 0
    for item in domestic:
        assert "average_market_value" in item

    # National team competitions (AFCON, WC qualifiers, etc.) come from the
    # headerless boxes on the confederation page — no country fields
    national_team = [i for i in items if "country_name" not in i]
    assert len(national_team) > 0


def test_competitions_fifa(tmp_path):
    """Feed the FIFA confederation to get World Cup and qualifier competitions."""
    items = run_crawler(
        "competitions",
        parents_data={"type": "confederation", "href": "/wettbewerbe/fifa"},
        tmp_path=tmp_path,
    )
    assert len(items) > 0
    for item in items:
        assert item["type"] == "competition"
        assert "href" in item
        assert "competition_name" in item
    hrefs = [item["href"] for item in items]
    assert any("world-cup" in h or "weltmeisterschaft" in h for h in hrefs)


# ---------------------------------------------------------------------------
# 3. Clubs (~25 requests — 1 small league)
# ---------------------------------------------------------------------------

def test_clubs(tmp_path):
    """Feed a single small league (Croatian 1.HNL, ~12 teams)."""
    items = run_crawler(
        "clubs",
        parents_data={
            "type": "competition",
            "competition_type": "first_tier",
            "href": "/1-hnl/startseite/wettbewerb/KR1",
        },
        tmp_path=tmp_path,
    )
    assert len(items) >= 10
    for item in items:
        assert item["type"] == "club"
        assert "href" in item
        assert "name" in item
        assert "squad_size" in item

    # New: club_image_url on all items, coach_href on most items
    for item in items:
        assert "club_image_url" in item
    assert any(item.get("coach_href") for item in items)


# ---------------------------------------------------------------------------
# 4. Players (~39 requests — 1 tiny club)
# ---------------------------------------------------------------------------

def test_players(tmp_path):
    """Feed a single small club (HNK Sibenik)."""
    items = run_crawler(
        "players",
        parents_data={
            "type": "club",
            "href": "/hnk-sibenik/startseite/verein/223",
        },
        tmp_path=tmp_path,
    )
    assert len(items) >= 5
    for item in items:
        assert item["type"] == "player"
        assert "href" in item
        assert "name" in item
        assert "date_of_birth" in item
        assert "position" in item

    # New: full_name should be present on most players
    assert any(item.get("full_name") for item in items)

    # New: additional_citizenships only present for multi-citizenship players (soft check)
    # New: national_team only for international players (soft check)


# ---------------------------------------------------------------------------
# 5. Appearances (2 requests — 1 player)
# ---------------------------------------------------------------------------

def test_appearances(tmp_path):
    """Feed a single player (Ayoze Perez)."""
    items = run_crawler(
        "appearances",
        parents_data={
            "type": "player",
            "href": "/ayoze-perez/profil/spieler/246968",
        },
        tmp_path=tmp_path,
    )
    assert len(items) >= 1
    for item in items:
        assert item["type"] == "appearance"
        assert "competition_code" in item
        assert "date" in item
        assert "result" in item


# ---------------------------------------------------------------------------
# 6. Games (3 requests — 1 domestic super cup = 1 game)
# ---------------------------------------------------------------------------

def test_games(tmp_path):
    """Feed a single super cup competition (DFL Supercup, typically 1 game)."""
    items = run_crawler(
        "games",
        parents_data={
            "type": "competition",
            "competition_type": "domestic_super_cup",
            "href": "/dfl-supercup/startseite/wettbewerb/DFL",
        },
        tmp_path=tmp_path,
    )
    assert len(items) >= 1
    game = items[0]
    assert game["type"] == "game"
    assert "game_id" in game
    assert "home_club" in game
    assert "away_club" in game
    assert "result" in game
    assert "events" in game
    assert isinstance(game["events"], list)

    # New: club names
    assert "home_club_name" in game
    assert "away_club_name" in game

    # New: referee_href
    assert "referee_href" in game

    # New: half_time_score and kickoff_time (may be None but key should exist)
    assert "half_time_score" in game
    assert "kickoff_time" in game

    # New: manager hrefs (if managers are present)
    if "home_manager" in game:
        assert "href" in game["home_manager"]
    if "away_manager" in game:
        assert "href" in game["away_manager"]


# ---------------------------------------------------------------------------
# 6b. Games — UEFA Euro (tournament competition, requires season=2023 for Euro 2024)
# ---------------------------------------------------------------------------

def test_games_euro(tmp_path):
    """Feed the UEFA Euro competition (saison_id=2023 = Euro 2024)."""
    items = run_crawler(
        "games",
        parents_data={
            "type": "competition",
            "competition_type": "uefa_euro",
            "href": "/uefa-euro/startseite/pokalwettbewerb/EURO",
            "competition_name": "UEFA Euro",
        },
        season=2023,
        tmp_path=tmp_path,
    )
    assert len(items) >= 51  # Euro 2024 had 51 games
    for item in items:
        assert item["type"] == "game"
        assert "game_id" in item
        assert "home_club" in item
        assert "away_club" in item
        assert "result" in item
        assert "date" in item


# ---------------------------------------------------------------------------
# 7. Game Lineups (2 requests — 1 game)
# ---------------------------------------------------------------------------

def test_game_lineups(tmp_path):
    """Feed a single game (DFL Supercup 2024)."""
    items = run_crawler(
        "game_lineups",
        parents_data={
            "type": "game",
            "game_id": 4357026,
            "href": "/spielbericht/index/spielbericht/4357026",
            "home_club": {"href": "/bayer-04-leverkusen/startseite/verein/15/saison_id/2024"},
            "away_club": {"href": "/vfb-stuttgart/startseite/verein/79/saison_id/2024"},
        },
        tmp_path=tmp_path,
    )
    assert len(items) == 1
    lineup = items[0]
    assert lineup["type"] == "game_lineups"
    assert lineup["game_id"] == 4357026
    assert "home_club" in lineup
    assert "away_club" in lineup
    assert len(lineup["home_club"]["starting_lineup"]) == 11
    assert len(lineup["away_club"]["starting_lineup"]) == 11
    assert lineup["home_club"]["formation"] is not None
    assert lineup["away_club"]["formation"] is not None

    # New: player nationality should be present on at least some players
    all_players = (
        lineup["home_club"]["starting_lineup"]
        + lineup["away_club"]["starting_lineup"]
    )
    assert any("player_nationality" in p for p in all_players)


# ---------------------------------------------------------------------------
# 8. Countries (~1 request — 1 small confederation)
# ---------------------------------------------------------------------------

def test_countries(tmp_path):
    """Feed a single confederation (afrika, 1 page) to minimize requests."""
    items = run_crawler(
        "countries",
        parents_data={"type": "confederation", "href": "/wettbewerbe/afrika"},
        tmp_path=tmp_path,
    )
    assert len(items) > 0
    for item in items:
        assert item["type"] == "country"
        assert "href" in item
        assert "country_id" in item
        assert "country_name" in item
        assert "country_code" in item
        assert "total_clubs" in item
        assert "total_players" in item


# ---------------------------------------------------------------------------
# 9. National Teams (~2 requests — 1 small country)
# ---------------------------------------------------------------------------

def test_national_teams(tmp_path):
    """Feed a single country (Wales, country_id=191)."""
    items = run_crawler(
        "national_teams",
        parents_data={
            "type": "country",
            "href": "/wettbewerbe/national/wettbewerbe/191",
            "country_id": "191",
            "country_name": "Wales",
        },
        tmp_path=tmp_path,
    )
    assert len(items) >= 1
    for item in items:
        assert item["type"] == "national_team"
        assert "href" in item
        assert "name" in item
        assert "squad_size" in item


# ---------------------------------------------------------------------------
# 10. National Team Players (~30 requests — 1 national team)
# ---------------------------------------------------------------------------

def test_national_team_players(tmp_path):
    """Feed a national team (Wales) as parent to players crawler."""
    items = run_crawler(
        "players",
        parents_data={
            "type": "national_team",
            "href": "/wales/startseite/verein/3864",
        },
        tmp_path=tmp_path,
    )
    assert len(items) >= 5
    for item in items:
        assert item["type"] == "player"
        assert "href" in item
        assert "name" in item
