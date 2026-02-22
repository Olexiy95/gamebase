"""Steam Web API client."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import requests

_BASE = "https://api.steampowered.com"
_TIMEOUT = 10  # seconds


class SteamAPIError(Exception):
    """Raised when the Steam API returns an unexpected response."""


class SteamClient:
    """Thin wrapper around the Steam Web API.

    Parameters
    ----------
    api_key:
        Your Steam Web API key (https://steamcommunity.com/dev/apikey).
    """

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("api_key must not be empty")
        self._key = api_key
        self._session = requests.Session()
        self._session.params = {"key": self._key, "format": "json"}  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, **params: Any) -> Any:
        url = f"{_BASE}/{path}"
        resp = self._session.get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def get_player_summary(self, steam_id: str) -> dict[str, Any]:
        """Return raw player summary data for *steam_id*.

        Raises ``SteamAPIError`` if the player is not found.
        """
        data = self._get(
            "ISteamUser/GetPlayerSummaries/v2/", steamids=steam_id
        )
        players = data.get("response", {}).get("players", [])
        if not players:
            raise SteamAPIError(f"Player not found for steam_id={steam_id!r}")
        return players[0]

    def get_owned_games(
        self, steam_id: str, include_free_games: bool = True
    ) -> list[dict[str, Any]]:
        """Return a list of owned games with playtime information."""
        data = self._get(
            "IPlayerService/GetOwnedGames/v1/",
            steamid=steam_id,
            include_appinfo=1,
            include_played_free_games=int(include_free_games),
        )
        return data.get("response", {}).get("games", [])

    def get_achievements(
        self, steam_id: str, app_id: int
    ) -> list[dict[str, Any]]:
        """Return achievement data for *app_id* owned by *steam_id*.

        Returns an empty list when the game has no achievements or the profile
        is private.
        """
        try:
            data = self._get(
                "ISteamUserStats/GetPlayerAchievements/v1/",
                steamid=steam_id,
                appid=app_id,
                l="english",
            )
        except requests.HTTPError:
            return []
        playerstats = data.get("playerstats", {})
        if not playerstats.get("success", False):
            return []
        return playerstats.get("achievements", [])

    def get_user_stats_for_game(
        self, steam_id: str, app_id: int
    ) -> list[dict[str, Any]]:
        """Return numeric stats for *app_id* owned by *steam_id*.

        Returns an empty list when unavailable.
        """
        try:
            data = self._get(
                "ISteamUserStats/GetUserStatsForGame/v2/",
                steamid=steam_id,
                appid=app_id,
            )
        except requests.HTTPError:
            return []
        playerstats = data.get("playerstats", {})
        return playerstats.get("stats", [])

    # ------------------------------------------------------------------
    # Convenience parsers
    # ------------------------------------------------------------------

    @staticmethod
    def parse_last_played(unix_ts: Optional[int]) -> Optional[datetime]:
        """Convert a Unix timestamp to a UTC-aware *datetime*, or ``None``."""
        if not unix_ts:
            return None
        return datetime.fromtimestamp(unix_ts, tz=timezone.utc)
