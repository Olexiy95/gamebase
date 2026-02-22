"""Data models for gamebase."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class SteamAccount:
    """Represents a Steam user account."""

    steam_id: str
    persona_name: str
    profile_url: str
    avatar_url: str = ""
    real_name: str = ""
    country_code: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.steam_id or not self.steam_id.isdigit():
            raise ValueError(f"Invalid steam_id: {self.steam_id!r}")


@dataclass
class Game:
    """Represents a tracked game."""

    app_id: int
    name: str
    playtime_minutes: int = 0
    last_played: Optional[datetime] = None
    img_icon_url: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if self.app_id <= 0:
            raise ValueError(f"Invalid app_id: {self.app_id}")
        if self.playtime_minutes < 0:
            raise ValueError("playtime_minutes cannot be negative")

    @property
    def playtime_hours(self) -> float:
        """Return playtime expressed in hours."""
        return round(self.playtime_minutes / 60, 2)


@dataclass
class Achievement:
    """Represents a single game achievement."""

    api_name: str
    display_name: str
    achieved: bool = False
    unlock_time: Optional[datetime] = None
    description: str = ""


@dataclass
class GameStats:
    """Stats for a specific game owned by a Steam account."""

    steam_id: str
    app_id: int
    game_name: str
    playtime_minutes: int = 0
    achievements_total: int = 0
    achievements_unlocked: int = 0
    achievements: list[Achievement] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def achievement_rate(self) -> float:
        """Return the fraction of achievements unlocked (0.0–1.0)."""
        if self.achievements_total == 0:
            return 0.0
        return round(self.achievements_unlocked / self.achievements_total, 4)

    @property
    def playtime_hours(self) -> float:
        return round(self.playtime_minutes / 60, 2)
