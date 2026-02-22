"""Tests for gamebase.db (Database)."""

import pytest

from gamebase.db import Database
from gamebase.models import Achievement, Game, GameStats, SteamAccount


@pytest.fixture()
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


class TestSteamAccountPersistence:
    def _account(self, steam_id="76561198000000001", name="Alice") -> SteamAccount:
        return SteamAccount(
            steam_id=steam_id,
            persona_name=name,
            profile_url=f"https://steamcommunity.com/id/{name}/",
            avatar_url="https://example.com/avatar.jpg",
            real_name="Alice Smith",
            country_code="US",
        )

    def test_upsert_and_get(self, db):
        acc = self._account()
        db.upsert_account(acc)
        result = db.get_account(acc.steam_id)
        assert result is not None
        assert result.persona_name == "Alice"
        assert result.country_code == "US"

    def test_upsert_updates_existing(self, db):
        acc = self._account()
        db.upsert_account(acc)
        acc.persona_name = "AliceUpdated"
        db.upsert_account(acc)
        result = db.get_account(acc.steam_id)
        assert result.persona_name == "AliceUpdated"

    def test_get_missing_returns_none(self, db):
        assert db.get_account("99999") is None

    def test_list_accounts(self, db):
        for i in range(3):
            db.upsert_account(self._account(steam_id=str(100 + i), name=f"User{i}"))
        accounts = db.list_accounts()
        assert len(accounts) == 3

    def test_delete_account(self, db):
        acc = self._account()
        db.upsert_account(acc)
        assert db.delete_account(acc.steam_id) is True
        assert db.get_account(acc.steam_id) is None

    def test_delete_missing_returns_false(self, db):
        assert db.delete_account("nonexistent") is False


class TestGamePersistence:
    def _game(self, app_id=570, name="Dota 2") -> Game:
        return Game(app_id=app_id, name=name, playtime_minutes=600)

    def test_upsert_and_get(self, db):
        game = self._game()
        db.upsert_game(game)
        result = db.get_game(game.app_id)
        assert result is not None
        assert result.name == "Dota 2"
        assert result.playtime_minutes == 600

    def test_upsert_updates_existing(self, db):
        game = self._game()
        db.upsert_game(game)
        game.playtime_minutes = 1200
        db.upsert_game(game)
        result = db.get_game(game.app_id)
        assert result.playtime_minutes == 1200

    def test_get_missing_returns_none(self, db):
        assert db.get_game(99999) is None

    def test_list_games_ordered_by_playtime(self, db):
        db.upsert_game(Game(app_id=1, name="A", playtime_minutes=100))
        db.upsert_game(Game(app_id=2, name="B", playtime_minutes=500))
        db.upsert_game(Game(app_id=3, name="C", playtime_minutes=50))
        games = db.list_games()
        assert [g.playtime_minutes for g in games] == [500, 100, 50]

    def test_delete_game(self, db):
        game = self._game()
        db.upsert_game(game)
        assert db.delete_game(game.app_id) is True
        assert db.get_game(game.app_id) is None

    def test_delete_missing_returns_false(self, db):
        assert db.delete_game(99999) is False


class TestGameStatsPersistence:
    def _stats(self, steam_id="76561198000000001", app_id=570) -> GameStats:
        achievements = [
            Achievement(api_name="ACH1", display_name="First", achieved=True),
            Achievement(api_name="ACH2", display_name="Second", achieved=False),
        ]
        return GameStats(
            steam_id=steam_id,
            app_id=app_id,
            game_name="Dota 2",
            playtime_minutes=600,
            achievements_total=2,
            achievements_unlocked=1,
            achievements=achievements,
        )

    def test_upsert_and_get(self, db):
        stats = self._stats()
        db.upsert_game_stats(stats)
        result = db.get_game_stats(stats.steam_id, stats.app_id)
        assert result is not None
        assert result.game_name == "Dota 2"
        assert result.achievements_unlocked == 1
        assert len(result.achievements) == 2

    def test_upsert_updates_existing(self, db):
        stats = self._stats()
        db.upsert_game_stats(stats)
        stats.achievements_unlocked = 2
        db.upsert_game_stats(stats)
        result = db.get_game_stats(stats.steam_id, stats.app_id)
        assert result.achievements_unlocked == 2

    def test_get_missing_returns_none(self, db):
        assert db.get_game_stats("0", 0) is None

    def test_list_game_stats(self, db):
        for app_id in [570, 730, 440]:
            db.upsert_game_stats(self._stats(app_id=app_id))
        all_stats = db.list_game_stats("76561198000000001")
        assert len(all_stats) == 3

    def test_achievements_stored_correctly(self, db):
        stats = self._stats()
        db.upsert_game_stats(stats)
        result = db.get_game_stats(stats.steam_id, stats.app_id)
        achieved_names = {a.api_name for a in result.achievements if a.achieved}
        assert achieved_names == {"ACH1"}
