"""Tests for gamebase.scraper (StatsScraper)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from gamebase.db import Database
from gamebase.models import Game
from gamebase.scraper import StatsScraper
from gamebase.steam import SteamClient


@pytest.fixture()
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


@pytest.fixture()
def client():
    return MagicMock(spec=SteamClient)


@pytest.fixture()
def scraper(client, db):
    return StatsScraper(client, db)


class TestScrapeAccount:
    def test_stores_account(self, scraper, client, db):
        client.get_player_summary.return_value = {
            "steamid": "76561198000000001",
            "personaname": "Alice",
            "profileurl": "https://steamcommunity.com/id/alice/",
            "avatarfull": "https://example.com/avatar.jpg",
            "realname": "Alice Smith",
            "loccountrycode": "US",
        }
        account = scraper.scrape_account("76561198000000001")
        assert account.persona_name == "Alice"
        stored = db.get_account("76561198000000001")
        assert stored is not None
        assert stored.country_code == "US"

    def test_missing_optional_fields(self, scraper, client, db):
        client.get_player_summary.return_value = {
            "steamid": "76561198000000002",
            "personaname": "Bob",
            "profileurl": "https://steamcommunity.com/id/bob/",
        }
        account = scraper.scrape_account("76561198000000002")
        assert account.avatar_url == ""
        assert account.country_code == ""


class TestScrapeOwnedGames:
    def test_stores_games(self, scraper, client, db):
        client.get_owned_games.return_value = [
            {"appid": 570, "name": "Dota 2", "playtime_forever": 600},
            {"appid": 730, "name": "CS:GO", "playtime_forever": 300},
        ]
        client.parse_last_played.return_value = None
        games = scraper.scrape_owned_games("76561198000000001")
        assert len(games) == 2
        stored = db.get_game(570)
        assert stored is not None
        assert stored.playtime_minutes == 600

    def test_skips_entries_without_appid(self, scraper, client, db):
        client.get_owned_games.return_value = [
            {"name": "Unknown"},
            {"appid": 570, "name": "Dota 2", "playtime_forever": 100},
        ]
        client.parse_last_played.return_value = None
        games = scraper.scrape_owned_games("76561198000000001")
        assert len(games) == 1


class TestScrapeGameStats:
    def test_stores_stats_with_achievements(self, scraper, client, db):
        # Pre-populate the game so it has a name and playtime
        db.upsert_game(Game(app_id=570, name="Dota 2", playtime_minutes=600))
        client.get_achievements.return_value = [
            {"apiname": "ACH1", "name": "First", "achieved": 1, "unlocktime": 1609459200},
            {"apiname": "ACH2", "name": "Second", "achieved": 0, "unlocktime": 0},
        ]
        stats = scraper.scrape_game_stats("76561198000000001", 570)
        assert stats.achievements_total == 2
        assert stats.achievements_unlocked == 1
        assert stats.game_name == "Dota 2"

    def test_fallback_name_when_game_not_in_db(self, scraper, client, db):
        client.get_achievements.return_value = []
        stats = scraper.scrape_game_stats("76561198000000001", 9999)
        assert stats.game_name == "App 9999"

    def test_scrape_all_skips_errors(self, scraper, client, db):
        db.upsert_game(Game(app_id=1, name="A"))
        db.upsert_game(Game(app_id=2, name="B"))
        # First call raises, second succeeds
        client.get_achievements.side_effect = [Exception("Network error"), []]
        results = scraper.scrape_all_game_stats("76561198000000001")
        assert len(results) == 1
