"""Stats scraper: fetch and persist player/game data from Steam."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from gamebase.db import Database
from gamebase.models import Achievement, Game, GameStats, SteamAccount
from gamebase.steam import SteamClient
from gamebase.tracker import GameTracker

logger = logging.getLogger(__name__)


class StatsScraper:
    """Fetches stats from the Steam API and stores them in the database.

    Parameters
    ----------
    client:
        An authenticated ``SteamClient`` instance.
    db:
        The ``Database`` to persist data into.
    """

    def __init__(self, client: SteamClient, db: Database) -> None:
        self._client = client
        self._db = db
        self._tracker = GameTracker(db)

    # ------------------------------------------------------------------
    # Account scraping
    # ------------------------------------------------------------------

    def scrape_account(self, steam_id: str) -> SteamAccount:
        """Fetch player summary for *steam_id* and persist it.

        Returns the resulting ``SteamAccount``.
        """
        raw = self._client.get_player_summary(steam_id)
        account = SteamAccount(
            steam_id=raw["steamid"],
            persona_name=raw.get("personaname", ""),
            profile_url=raw.get("profileurl", ""),
            avatar_url=raw.get("avatarfull", raw.get("avatar", "")),
            real_name=raw.get("realname", ""),
            country_code=raw.get("loccountrycode", ""),
            created_at=datetime.now(tz=timezone.utc),
        )
        self._db.upsert_account(account)
        return account

    # ------------------------------------------------------------------
    # Game library scraping
    # ------------------------------------------------------------------

    def scrape_owned_games(self, steam_id: str) -> list[Game]:
        """Fetch owned games for *steam_id* and persist them.

        Returns the list of ``Game`` objects imported.
        """
        raw_games = self._client.get_owned_games(steam_id)
        games: list[Game] = []
        for raw in raw_games:
            app_id = raw.get("appid")
            if not app_id:
                continue
            last_played = self._client.parse_last_played(
                raw.get("rtime_last_played")
            )
            game = Game(
                app_id=app_id,
                name=raw.get("name", f"App {app_id}"),
                playtime_minutes=raw.get("playtime_forever", 0),
                last_played=last_played,
                img_icon_url=raw.get("img_icon_url", ""),
            )
            games.append(game)
        self._tracker.import_games(games)
        return games

    # ------------------------------------------------------------------
    # Achievement / stats scraping
    # ------------------------------------------------------------------

    def scrape_game_stats(self, steam_id: str, app_id: int) -> GameStats:
        """Fetch and persist achievement stats for one game.

        Returns the resulting ``GameStats``.
        """
        raw_achievements = self._client.get_achievements(steam_id, app_id)
        achievements: list[Achievement] = []
        for ach in raw_achievements:
            unlock_ts = ach.get("unlocktime")
            unlock_time = (
                datetime.fromtimestamp(unlock_ts, tz=timezone.utc)
                if unlock_ts
                else None
            )
            achievements.append(
                Achievement(
                    api_name=ach.get("apiname", ""),
                    display_name=ach.get("name", ""),
                    achieved=bool(ach.get("achieved", 0)),
                    unlock_time=unlock_time,
                    description=ach.get("description", ""),
                )
            )

        unlocked = sum(1 for a in achievements if a.achieved)
        game = self._db.get_game(app_id)
        game_name = game.name if game else f"App {app_id}"
        playtime = game.playtime_minutes if game else 0

        stats = GameStats(
            steam_id=steam_id,
            app_id=app_id,
            game_name=game_name,
            playtime_minutes=playtime,
            achievements_total=len(achievements),
            achievements_unlocked=unlocked,
            achievements=achievements,
            fetched_at=datetime.now(tz=timezone.utc),
        )
        self._db.upsert_game_stats(stats)
        return stats

    def scrape_all_game_stats(
        self, steam_id: str, app_ids: list[int] | None = None
    ) -> list[GameStats]:
        """Scrape achievement stats for all *app_ids* (or all tracked games).

        Returns the list of ``GameStats`` objects fetched.
        """
        if app_ids is None:
            app_ids = [g.app_id for g in self._db.list_games()]

        results: list[GameStats] = []
        for app_id in app_ids:
            try:
                stats = self.scrape_game_stats(steam_id, app_id)
                results.append(stats)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping app_id=%d: %s", app_id, exc)
        return results
