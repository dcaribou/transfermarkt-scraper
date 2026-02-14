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
    assert len(items) == 4
    for item in items:
        assert item["type"] == "confederation"
        assert item["href"].startswith("/wettbewerbe/")


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
