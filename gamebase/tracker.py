"""Game tracker: add, update, list and remove games from the local database."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from gamebase.db import Database
from gamebase.models import Game


class GameTracker:
    """Manages the local collection of tracked games."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_game(
        self,
        app_id: int,
        name: str,
        playtime_minutes: int = 0,
        last_played: Optional[datetime] = None,
        img_icon_url: str = "",
        notes: str = "",
    ) -> Game:
        """Add or update a game in the tracker.

        If the game already exists the record is updated (upsert semantics).
        """
        game = Game(
            app_id=app_id,
            name=name,
            playtime_minutes=playtime_minutes,
            last_played=last_played,
            img_icon_url=img_icon_url,
            notes=notes,
        )
        self._db.upsert_game(game)
        return game

    def update_playtime(self, app_id: int, playtime_minutes: int) -> Game:
        """Update the playtime for an existing game.

        Raises ``KeyError`` if the game is not tracked.
        """
        game = self._db.get_game(app_id)
        if game is None:
            raise KeyError(f"Game with app_id={app_id} is not tracked")
        game.playtime_minutes = playtime_minutes
        self._db.upsert_game(game)
        return game

    def update_notes(self, app_id: int, notes: str) -> Game:
        """Update personal notes for a game.

        Raises ``KeyError`` if the game is not tracked.
        """
        game = self._db.get_game(app_id)
        if game is None:
            raise KeyError(f"Game with app_id={app_id} is not tracked")
        game.notes = notes
        self._db.upsert_game(game)
        return game

    def remove_game(self, app_id: int) -> bool:
        """Remove a game from the tracker.

        Returns ``True`` if the game was found and removed, ``False`` otherwise.
        """
        return self._db.delete_game(app_id)

    def get_game(self, app_id: int) -> Optional[Game]:
        """Return a tracked game or ``None`` if not found."""
        return self._db.get_game(app_id)

    def list_games(self) -> list[Game]:
        """Return all tracked games ordered by playtime (descending)."""
        return self._db.list_games()

    # ------------------------------------------------------------------
    # Bulk import
    # ------------------------------------------------------------------

    def import_games(self, games: list[Game]) -> int:
        """Bulk-import a list of ``Game`` objects (upsert semantics).

        Returns the number of games imported.
        """
        for game in games:
            self._db.upsert_game(game)
        return len(games)
