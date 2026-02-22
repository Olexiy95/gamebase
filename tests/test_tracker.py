"""Tests for gamebase.tracker (GameTracker)."""

import pytest

from gamebase.db import Database
from gamebase.models import Game
from gamebase.tracker import GameTracker


@pytest.fixture()
def tracker(tmp_path):
    db = Database(tmp_path / "test.db")
    t = GameTracker(db)
    yield t
    db.close()


class TestGameTracker:
    def test_add_and_get_game(self, tracker):
        game = tracker.add_game(570, "Dota 2", playtime_minutes=120)
        assert game.app_id == 570
        result = tracker.get_game(570)
        assert result is not None
        assert result.name == "Dota 2"

    def test_add_game_upserts(self, tracker):
        tracker.add_game(570, "Dota 2", playtime_minutes=60)
        tracker.add_game(570, "Dota 2", playtime_minutes=120)
        game = tracker.get_game(570)
        assert game.playtime_minutes == 120

    def test_list_games_empty(self, tracker):
        assert tracker.list_games() == []

    def test_list_games_multiple(self, tracker):
        tracker.add_game(1, "Alpha", playtime_minutes=300)
        tracker.add_game(2, "Beta", playtime_minutes=100)
        tracker.add_game(3, "Gamma", playtime_minutes=500)
        games = tracker.list_games()
        assert len(games) == 3
        # Ordered by playtime descending
        assert games[0].app_id == 3

    def test_update_playtime(self, tracker):
        tracker.add_game(570, "Dota 2", playtime_minutes=60)
        updated = tracker.update_playtime(570, 180)
        assert updated.playtime_minutes == 180

    def test_update_playtime_unknown_game_raises(self, tracker):
        with pytest.raises(KeyError):
            tracker.update_playtime(9999, 100)

    def test_update_notes(self, tracker):
        tracker.add_game(570, "Dota 2")
        game = tracker.update_notes(570, "Great game!")
        assert game.notes == "Great game!"

    def test_update_notes_unknown_game_raises(self, tracker):
        with pytest.raises(KeyError):
            tracker.update_notes(9999, "Note")

    def test_remove_existing_game(self, tracker):
        tracker.add_game(570, "Dota 2")
        assert tracker.remove_game(570) is True
        assert tracker.get_game(570) is None

    def test_remove_missing_game(self, tracker):
        assert tracker.remove_game(9999) is False

    def test_import_games(self, tracker):
        games = [
            Game(app_id=1, name="A", playtime_minutes=10),
            Game(app_id=2, name="B", playtime_minutes=20),
            Game(app_id=3, name="C", playtime_minutes=30),
        ]
        count = tracker.import_games(games)
        assert count == 3
        assert tracker.get_game(2) is not None
