"""SQLite database layer for gamebase."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

from gamebase.models import Achievement, Game, GameStats, SteamAccount

_DEFAULT_DB = Path.home() / ".gamebase" / "gamebase.db"

_DDL = """
CREATE TABLE IF NOT EXISTS steam_accounts (
    steam_id     TEXT PRIMARY KEY,
    persona_name TEXT NOT NULL,
    profile_url  TEXT NOT NULL,
    avatar_url   TEXT NOT NULL DEFAULT '',
    real_name    TEXT NOT NULL DEFAULT '',
    country_code TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS games (
    app_id           INTEGER PRIMARY KEY,
    name             TEXT NOT NULL,
    playtime_minutes INTEGER NOT NULL DEFAULT 0,
    last_played      TEXT,
    img_icon_url     TEXT NOT NULL DEFAULT '',
    notes            TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS game_stats (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id               TEXT NOT NULL,
    app_id                 INTEGER NOT NULL,
    game_name              TEXT NOT NULL,
    playtime_minutes       INTEGER NOT NULL DEFAULT 0,
    achievements_total     INTEGER NOT NULL DEFAULT 0,
    achievements_unlocked  INTEGER NOT NULL DEFAULT 0,
    fetched_at             TEXT NOT NULL,
    UNIQUE(steam_id, app_id)
);

CREATE TABLE IF NOT EXISTS achievements (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id     TEXT NOT NULL,
    app_id       INTEGER NOT NULL,
    api_name     TEXT NOT NULL,
    display_name TEXT NOT NULL,
    achieved     INTEGER NOT NULL DEFAULT 0,
    unlock_time  TEXT,
    description  TEXT NOT NULL DEFAULT '',
    UNIQUE(steam_id, app_id, api_name)
);
"""


def _fmt_dt(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(value) if value else None


class Database:
    """Thin wrapper around an SQLite connection for gamebase data."""

    def __init__(self, path: Path | str = _DEFAULT_DB) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._apply_schema()

    def _apply_schema(self) -> None:
        self._conn.executescript(_DDL)
        self._conn.commit()

    @contextmanager
    def _tx(self) -> Generator[sqlite3.Connection, None, None]:
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Steam Accounts
    # ------------------------------------------------------------------

    def upsert_account(self, account: SteamAccount) -> None:
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO steam_accounts
                    (steam_id, persona_name, profile_url, avatar_url,
                     real_name, country_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(steam_id) DO UPDATE SET
                    persona_name = excluded.persona_name,
                    profile_url  = excluded.profile_url,
                    avatar_url   = excluded.avatar_url,
                    real_name    = excluded.real_name,
                    country_code = excluded.country_code
                """,
                (
                    account.steam_id,
                    account.persona_name,
                    account.profile_url,
                    account.avatar_url,
                    account.real_name,
                    account.country_code,
                    _fmt_dt(account.created_at),
                ),
            )

    def get_account(self, steam_id: str) -> Optional[SteamAccount]:
        row = self._conn.execute(
            "SELECT * FROM steam_accounts WHERE steam_id = ?", (steam_id,)
        ).fetchone()
        if row is None:
            return None
        return SteamAccount(
            steam_id=row["steam_id"],
            persona_name=row["persona_name"],
            profile_url=row["profile_url"],
            avatar_url=row["avatar_url"],
            real_name=row["real_name"],
            country_code=row["country_code"],
            created_at=_parse_dt(row["created_at"]) or datetime.now(timezone.utc),
        )

    def list_accounts(self) -> list[SteamAccount]:
        rows = self._conn.execute("SELECT * FROM steam_accounts").fetchall()
        return [
            SteamAccount(
                steam_id=r["steam_id"],
                persona_name=r["persona_name"],
                profile_url=r["profile_url"],
                avatar_url=r["avatar_url"],
                real_name=r["real_name"],
                country_code=r["country_code"],
                created_at=_parse_dt(r["created_at"]) or datetime.now(timezone.utc),
            )
            for r in rows
        ]

    def delete_account(self, steam_id: str) -> bool:
        with self._tx() as conn:
            cur = conn.execute(
                "DELETE FROM steam_accounts WHERE steam_id = ?", (steam_id,)
            )
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Games
    # ------------------------------------------------------------------

    def upsert_game(self, game: Game) -> None:
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO games
                    (app_id, name, playtime_minutes, last_played, img_icon_url, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(app_id) DO UPDATE SET
                    name             = excluded.name,
                    playtime_minutes = excluded.playtime_minutes,
                    last_played      = excluded.last_played,
                    img_icon_url     = excluded.img_icon_url,
                    notes            = excluded.notes
                """,
                (
                    game.app_id,
                    game.name,
                    game.playtime_minutes,
                    _fmt_dt(game.last_played),
                    game.img_icon_url,
                    game.notes,
                ),
            )

    def get_game(self, app_id: int) -> Optional[Game]:
        row = self._conn.execute(
            "SELECT * FROM games WHERE app_id = ?", (app_id,)
        ).fetchone()
        if row is None:
            return None
        return Game(
            app_id=row["app_id"],
            name=row["name"],
            playtime_minutes=row["playtime_minutes"],
            last_played=_parse_dt(row["last_played"]),
            img_icon_url=row["img_icon_url"],
            notes=row["notes"],
        )

    def list_games(self) -> list[Game]:
        rows = self._conn.execute(
            "SELECT * FROM games ORDER BY playtime_minutes DESC"
        ).fetchall()
        return [
            Game(
                app_id=r["app_id"],
                name=r["name"],
                playtime_minutes=r["playtime_minutes"],
                last_played=_parse_dt(r["last_played"]),
                img_icon_url=r["img_icon_url"],
                notes=r["notes"],
            )
            for r in rows
        ]

    def delete_game(self, app_id: int) -> bool:
        with self._tx() as conn:
            cur = conn.execute("DELETE FROM games WHERE app_id = ?", (app_id,))
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Game Stats
    # ------------------------------------------------------------------

    def upsert_game_stats(self, stats: GameStats) -> None:
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO game_stats
                    (steam_id, app_id, game_name, playtime_minutes,
                     achievements_total, achievements_unlocked, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(steam_id, app_id) DO UPDATE SET
                    game_name              = excluded.game_name,
                    playtime_minutes       = excluded.playtime_minutes,
                    achievements_total     = excluded.achievements_total,
                    achievements_unlocked  = excluded.achievements_unlocked,
                    fetched_at             = excluded.fetched_at
                """,
                (
                    stats.steam_id,
                    stats.app_id,
                    stats.game_name,
                    stats.playtime_minutes,
                    stats.achievements_total,
                    stats.achievements_unlocked,
                    _fmt_dt(stats.fetched_at),
                ),
            )
            for ach in stats.achievements:
                conn.execute(
                    """
                    INSERT INTO achievements
                        (steam_id, app_id, api_name, display_name, achieved,
                         unlock_time, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(steam_id, app_id, api_name) DO UPDATE SET
                        display_name = excluded.display_name,
                        achieved     = excluded.achieved,
                        unlock_time  = excluded.unlock_time,
                        description  = excluded.description
                    """,
                    (
                        stats.steam_id,
                        stats.app_id,
                        ach.api_name,
                        ach.display_name,
                        int(ach.achieved),
                        _fmt_dt(ach.unlock_time),
                        ach.description,
                    ),
                )

    def get_game_stats(self, steam_id: str, app_id: int) -> Optional[GameStats]:
        row = self._conn.execute(
            "SELECT * FROM game_stats WHERE steam_id = ? AND app_id = ?",
            (steam_id, app_id),
        ).fetchone()
        if row is None:
            return None
        achievements = self._load_achievements(steam_id, app_id)
        return GameStats(
            steam_id=row["steam_id"],
            app_id=row["app_id"],
            game_name=row["game_name"],
            playtime_minutes=row["playtime_minutes"],
            achievements_total=row["achievements_total"],
            achievements_unlocked=row["achievements_unlocked"],
            achievements=achievements,
            fetched_at=_parse_dt(row["fetched_at"]) or datetime.now(timezone.utc),
        )

    def list_game_stats(self, steam_id: str) -> list[GameStats]:
        rows = self._conn.execute(
            "SELECT * FROM game_stats WHERE steam_id = ? ORDER BY playtime_minutes DESC",
            (steam_id,),
        ).fetchall()
        return [
            GameStats(
                steam_id=r["steam_id"],
                app_id=r["app_id"],
                game_name=r["game_name"],
                playtime_minutes=r["playtime_minutes"],
                achievements_total=r["achievements_total"],
                achievements_unlocked=r["achievements_unlocked"],
                achievements=self._load_achievements(r["steam_id"], r["app_id"]),
                fetched_at=_parse_dt(r["fetched_at"]) or datetime.now(timezone.utc),
            )
            for r in rows
        ]

    def _load_achievements(self, steam_id: str, app_id: int) -> list[Achievement]:
        rows = self._conn.execute(
            "SELECT * FROM achievements WHERE steam_id = ? AND app_id = ?",
            (steam_id, app_id),
        ).fetchall()
        return [
            Achievement(
                api_name=r["api_name"],
                display_name=r["display_name"],
                achieved=bool(r["achieved"]),
                unlock_time=_parse_dt(r["unlock_time"]),
                description=r["description"],
            )
            for r in rows
        ]
