"""Tests for gamebase.models."""

from datetime import datetime

import pytest

from gamebase.models import Achievement, Game, GameStats, SteamAccount


class TestSteamAccount:
    def test_valid_creation(self):
        acc = SteamAccount(
            steam_id="76561198000000000",
            persona_name="TestUser",
            profile_url="https://steamcommunity.com/id/testuser/",
        )
        assert acc.steam_id == "76561198000000000"
        assert acc.persona_name == "TestUser"

    def test_invalid_steam_id_empty(self):
        with pytest.raises(ValueError):
            SteamAccount(steam_id="", persona_name="x", profile_url="y")

    def test_invalid_steam_id_non_numeric(self):
        with pytest.raises(ValueError):
            SteamAccount(steam_id="abc", persona_name="x", profile_url="y")


class TestGame:
    def test_valid_creation(self):
        game = Game(app_id=570, name="Dota 2", playtime_minutes=3600)
        assert game.app_id == 570
        assert game.playtime_hours == 60.0

    def test_playtime_hours_rounding(self):
        game = Game(app_id=1, name="X", playtime_minutes=90)
        assert game.playtime_hours == 1.5

    def test_invalid_app_id(self):
        with pytest.raises(ValueError):
            Game(app_id=0, name="X")

    def test_negative_playtime(self):
        with pytest.raises(ValueError):
            Game(app_id=1, name="X", playtime_minutes=-1)

    def test_default_playtime(self):
        game = Game(app_id=1, name="Y")
        assert game.playtime_minutes == 0
        assert game.playtime_hours == 0.0


class TestAchievement:
    def test_default_not_achieved(self):
        ach = Achievement(api_name="WIN_GAME", display_name="Win the game")
        assert ach.achieved is False
        assert ach.unlock_time is None

    def test_achieved(self):
        ts = datetime(2023, 1, 1)
        ach = Achievement(api_name="ACH1", display_name="First", achieved=True, unlock_time=ts)
        assert ach.achieved is True
        assert ach.unlock_time == ts


class TestGameStats:
    def _make_stats(self, total: int, unlocked: int) -> GameStats:
        return GameStats(
            steam_id="12345",
            app_id=1,
            game_name="Test",
            achievements_total=total,
            achievements_unlocked=unlocked,
        )

    def test_achievement_rate_zero_when_no_achievements(self):
        stats = self._make_stats(0, 0)
        assert stats.achievement_rate == 0.0

    def test_achievement_rate_full(self):
        stats = self._make_stats(10, 10)
        assert stats.achievement_rate == 1.0

    def test_achievement_rate_partial(self):
        stats = self._make_stats(4, 1)
        assert stats.achievement_rate == 0.25

    def test_playtime_hours(self):
        stats = GameStats(
            steam_id="1",
            app_id=1,
            game_name="G",
            playtime_minutes=120,
        )
        assert stats.playtime_hours == 2.0
