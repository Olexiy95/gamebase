"""Stats analyser: derive insights from stored game and achievement data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from gamebase.db import Database
from gamebase.models import GameStats


@dataclass
class GameSummary:
    """Summarised view of a single game's stats."""

    app_id: int
    game_name: str
    playtime_hours: float
    achievements_total: int
    achievements_unlocked: int
    achievement_rate: float  # 0.0 – 1.0


@dataclass
class LibrarySummary:
    """Aggregate summary for an entire Steam library."""

    steam_id: str
    total_games: int
    total_playtime_hours: float
    total_achievements_total: int
    total_achievements_unlocked: int
    overall_achievement_rate: float
    top_played: list[GameSummary] = field(default_factory=list)
    most_complete: list[GameSummary] = field(default_factory=list)
    least_played: list[GameSummary] = field(default_factory=list)


class StatsAnalyser:
    """Analyses game statistics stored in the database.

    Parameters
    ----------
    db:
        The ``Database`` to read data from.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Per-game helpers
    # ------------------------------------------------------------------

    def game_summary(self, steam_id: str, app_id: int) -> Optional[GameSummary]:
        """Return a ``GameSummary`` for a specific game, or ``None``."""
        stats = self._db.get_game_stats(steam_id, app_id)
        if stats is None:
            return None
        return self._to_summary(stats)

    # ------------------------------------------------------------------
    # Library-wide analysis
    # ------------------------------------------------------------------

    def library_summary(self, steam_id: str, top_n: int = 5) -> LibrarySummary:
        """Return an aggregate ``LibrarySummary`` for *steam_id*.

        Parameters
        ----------
        top_n:
            How many games to include in each "top" list.
        """
        all_stats = self._db.list_game_stats(steam_id)
        summaries = [self._to_summary(s) for s in all_stats]

        total_playtime = sum(s.playtime_hours for s in summaries)
        total_ach_total = sum(s.achievements_total for s in summaries)
        total_ach_unlocked = sum(s.achievements_unlocked for s in summaries)
        overall_rate = (
            round(total_ach_unlocked / total_ach_total, 4)
            if total_ach_total > 0
            else 0.0
        )

        top_played = sorted(summaries, key=lambda s: s.playtime_hours, reverse=True)[
            :top_n
        ]
        most_complete = sorted(
            [s for s in summaries if s.achievements_total > 0],
            key=lambda s: s.achievement_rate,
            reverse=True,
        )[:top_n]
        least_played = sorted(summaries, key=lambda s: s.playtime_hours)[:top_n]

        return LibrarySummary(
            steam_id=steam_id,
            total_games=len(summaries),
            total_playtime_hours=round(total_playtime, 2),
            total_achievements_total=total_ach_total,
            total_achievements_unlocked=total_ach_unlocked,
            overall_achievement_rate=overall_rate,
            top_played=top_played,
            most_complete=most_complete,
            least_played=least_played,
        )

    # ------------------------------------------------------------------
    # Filtered queries
    # ------------------------------------------------------------------

    def unplayed_games(self, steam_id: str) -> list[GameSummary]:
        """Return games with zero playtime."""
        return [
            self._to_summary(s)
            for s in self._db.list_game_stats(steam_id)
            if s.playtime_minutes == 0
        ]

    def completed_games(self, steam_id: str) -> list[GameSummary]:
        """Return games where all achievements have been unlocked."""
        return [
            self._to_summary(s)
            for s in self._db.list_game_stats(steam_id)
            if s.achievements_total > 0
            and s.achievements_unlocked == s.achievements_total
        ]

    def games_above_playtime(
        self, steam_id: str, min_hours: float
    ) -> list[GameSummary]:
        """Return games with at least *min_hours* of playtime."""
        min_minutes = min_hours * 60
        return [
            self._to_summary(s)
            for s in self._db.list_game_stats(steam_id)
            if s.playtime_minutes >= min_minutes
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_summary(stats: GameStats) -> GameSummary:
        return GameSummary(
            app_id=stats.app_id,
            game_name=stats.game_name,
            playtime_hours=stats.playtime_hours,
            achievements_total=stats.achievements_total,
            achievements_unlocked=stats.achievements_unlocked,
            achievement_rate=stats.achievement_rate,
        )
