"""Tests for gamebase.analyser (StatsAnalyser)."""

import pytest

from gamebase.analyser import StatsAnalyser
from gamebase.db import Database
from gamebase.models import Achievement, Game, GameStats


@pytest.fixture()
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


@pytest.fixture()
def analyser(db):
    return StatsAnalyser(db)


def _add_stats(
    db: Database,
    steam_id: str,
    app_id: int,
    name: str,
    playtime_minutes: int,
    ach_total: int = 0,
    ach_unlocked: int = 0,
) -> GameStats:
    stats = GameStats(
        steam_id=steam_id,
        app_id=app_id,
        game_name=name,
        playtime_minutes=playtime_minutes,
        achievements_total=ach_total,
        achievements_unlocked=ach_unlocked,
    )
    db.upsert_game_stats(stats)
    return stats


STEAM_ID = "76561198000000001"


class TestGameSummary:
    def test_returns_summary_for_existing_game(self, analyser, db):
        _add_stats(db, STEAM_ID, 570, "Dota 2", 600, 10, 5)
        summary = analyser.game_summary(STEAM_ID, 570)
        assert summary is not None
        assert summary.game_name == "Dota 2"
        assert summary.playtime_hours == 10.0
        assert summary.achievement_rate == 0.5

    def test_returns_none_for_missing_game(self, analyser):
        assert analyser.game_summary(STEAM_ID, 9999) is None


class TestLibrarySummary:
    def test_empty_library(self, analyser):
        summary = analyser.library_summary(STEAM_ID)
        assert summary.total_games == 0
        assert summary.total_playtime_hours == 0.0
        assert summary.overall_achievement_rate == 0.0

    def test_basic_aggregation(self, analyser, db):
        _add_stats(db, STEAM_ID, 1, "Game A", 120, 10, 10)
        _add_stats(db, STEAM_ID, 2, "Game B", 60, 5, 2)
        _add_stats(db, STEAM_ID, 3, "Game C", 0, 0, 0)
        summary = analyser.library_summary(STEAM_ID)
        assert summary.total_games == 3
        assert summary.total_playtime_hours == pytest.approx(3.0)
        assert summary.total_achievements_total == 15
        assert summary.total_achievements_unlocked == 12
        assert summary.overall_achievement_rate == pytest.approx(0.8)

    def test_top_played_order(self, analyser, db):
        _add_stats(db, STEAM_ID, 1, "A", 30)
        _add_stats(db, STEAM_ID, 2, "B", 600)
        _add_stats(db, STEAM_ID, 3, "C", 120)
        summary = analyser.library_summary(STEAM_ID, top_n=3)
        assert summary.top_played[0].game_name == "B"

    def test_most_complete_order(self, analyser, db):
        _add_stats(db, STEAM_ID, 1, "A", 0, 10, 10)  # 100%
        _add_stats(db, STEAM_ID, 2, "B", 0, 10, 5)   # 50%
        summary = analyser.library_summary(STEAM_ID, top_n=5)
        assert summary.most_complete[0].game_name == "A"


class TestFilteredQueries:
    def test_unplayed_games(self, analyser, db):
        _add_stats(db, STEAM_ID, 1, "Played", 100)
        _add_stats(db, STEAM_ID, 2, "Unplayed", 0)
        unplayed = analyser.unplayed_games(STEAM_ID)
        assert len(unplayed) == 1
        assert unplayed[0].game_name == "Unplayed"

    def test_completed_games(self, analyser, db):
        _add_stats(db, STEAM_ID, 1, "Done", 60, 5, 5)
        _add_stats(db, STEAM_ID, 2, "Partial", 60, 5, 3)
        _add_stats(db, STEAM_ID, 3, "NoAch", 60, 0, 0)
        completed = analyser.completed_games(STEAM_ID)
        assert len(completed) == 1
        assert completed[0].game_name == "Done"

    def test_games_above_playtime(self, analyser, db):
        _add_stats(db, STEAM_ID, 1, "Long", 600)    # 10h
        _add_stats(db, STEAM_ID, 2, "Short", 30)    # 0.5h
        _add_stats(db, STEAM_ID, 3, "Medium", 300)  # 5h
        result = analyser.games_above_playtime(STEAM_ID, min_hours=5.0)
        names = {g.game_name for g in result}
        assert "Long" in names
        assert "Medium" in names
        assert "Short" not in names
