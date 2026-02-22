"""Command-line interface for gamebase."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from gamebase.analyser import StatsAnalyser
from gamebase.db import Database
from gamebase.models import SteamAccount
from gamebase.scraper import StatsScraper
from gamebase.steam import SteamClient
from gamebase.tracker import GameTracker

_DEFAULT_DB = Path.home() / ".gamebase" / "gamebase.db"


def _get_db(args: argparse.Namespace) -> Database:
    path = getattr(args, "db", None) or _DEFAULT_DB
    return Database(path)


def _get_client(args: argparse.Namespace) -> SteamClient:
    api_key = getattr(args, "api_key", None) or os.environ.get("STEAM_API_KEY", "")
    if not api_key:
        print(
            "Error: Steam API key required. Set STEAM_API_KEY or use --api-key.",
            file=sys.stderr,
        )
        sys.exit(1)
    return SteamClient(api_key)


# ------------------------------------------------------------------
# Sub-command handlers
# ------------------------------------------------------------------


def cmd_account_add(args: argparse.Namespace) -> None:
    db = _get_db(args)
    client = _get_client(args)
    scraper = StatsScraper(client, db)
    account = scraper.scrape_account(args.steam_id)
    print(
        f"Added account: {account.persona_name} ({account.steam_id})"
    )


def cmd_account_list(args: argparse.Namespace) -> None:
    db = _get_db(args)
    accounts = db.list_accounts()
    if not accounts:
        print("No accounts stored.")
        return
    for acc in accounts:
        print(f"  {acc.steam_id}  {acc.persona_name}  {acc.profile_url}")


def cmd_account_remove(args: argparse.Namespace) -> None:
    db = _get_db(args)
    removed = db.delete_account(args.steam_id)
    if removed:
        print(f"Removed account {args.steam_id}.")
    else:
        print(f"Account {args.steam_id} not found.", file=sys.stderr)


def cmd_games_import(args: argparse.Namespace) -> None:
    db = _get_db(args)
    client = _get_client(args)
    scraper = StatsScraper(client, db)
    games = scraper.scrape_owned_games(args.steam_id)
    print(f"Imported {len(games)} games for {args.steam_id}.")


def cmd_games_list(args: argparse.Namespace) -> None:
    db = _get_db(args)
    tracker = GameTracker(db)
    games = tracker.list_games()
    if not games:
        print("No games tracked.")
        return
    print(f"{'AppID':<12} {'Hours':>8}  Name")
    print("-" * 50)
    for game in games:
        print(f"{game.app_id:<12} {game.playtime_hours:>8.1f}  {game.name}")


def cmd_games_add(args: argparse.Namespace) -> None:
    db = _get_db(args)
    tracker = GameTracker(db)
    game = tracker.add_game(args.app_id, args.name, notes=args.notes or "")
    print(f"Added game: {game.name} (app_id={game.app_id})")


def cmd_games_remove(args: argparse.Namespace) -> None:
    db = _get_db(args)
    tracker = GameTracker(db)
    removed = tracker.remove_game(args.app_id)
    if removed:
        print(f"Removed game {args.app_id}.")
    else:
        print(f"Game {args.app_id} not found.", file=sys.stderr)


def cmd_scrape(args: argparse.Namespace) -> None:
    db = _get_db(args)
    client = _get_client(args)
    scraper = StatsScraper(client, db)
    app_ids = args.app_ids if args.app_ids else None
    results = scraper.scrape_all_game_stats(args.steam_id, app_ids=app_ids)
    print(f"Scraped stats for {len(results)} games.")


def cmd_analyse(args: argparse.Namespace) -> None:
    db = _get_db(args)
    analyser = StatsAnalyser(db)
    summary = analyser.library_summary(args.steam_id, top_n=args.top_n)

    print(f"\n=== Library summary for {args.steam_id} ===")
    print(f"  Total games tracked : {summary.total_games}")
    print(f"  Total playtime      : {summary.total_playtime_hours:.1f} hours")
    print(
        f"  Achievements        : {summary.total_achievements_unlocked}"
        f" / {summary.total_achievements_total}"
        f" ({summary.overall_achievement_rate * 100:.1f}%)"
    )

    if summary.top_played:
        print(f"\n  Top {args.top_n} most-played games:")
        for g in summary.top_played:
            print(f"    {g.playtime_hours:>8.1f}h  {g.game_name}")

    if summary.most_complete:
        print(f"\n  Top {args.top_n} most-completed games:")
        for g in summary.most_complete:
            pct = g.achievement_rate * 100
            print(f"    {pct:>5.1f}%  {g.game_name}")

    unplayed = analyser.unplayed_games(args.steam_id)
    print(f"\n  Unplayed games      : {len(unplayed)}")

    completed = analyser.completed_games(args.steam_id)
    print(f"  Fully completed     : {len(completed)}")


# ------------------------------------------------------------------
# Argument parser
# ------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gamebase",
        description="Game tracking, Steam account management, stats scraping and analysis.",
    )
    parser.add_argument(
        "--db",
        metavar="PATH",
        default=None,
        help="Path to the SQLite database file (default: ~/.gamebase/gamebase.db)",
    )
    parser.add_argument(
        "--api-key",
        dest="api_key",
        metavar="KEY",
        default=None,
        help="Steam Web API key (overrides STEAM_API_KEY env var)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- account ---
    account_p = subparsers.add_parser("account", help="Manage Steam accounts")
    account_sub = account_p.add_subparsers(dest="account_cmd", required=True)

    acc_add = account_sub.add_parser("add", help="Add/refresh a Steam account")
    acc_add.add_argument("steam_id", help="Steam 64-bit user ID")
    acc_add.set_defaults(func=cmd_account_add)

    acc_list = account_sub.add_parser("list", help="List stored Steam accounts")
    acc_list.set_defaults(func=cmd_account_list)

    acc_rm = account_sub.add_parser("remove", help="Remove a Steam account")
    acc_rm.add_argument("steam_id", help="Steam 64-bit user ID")
    acc_rm.set_defaults(func=cmd_account_remove)

    # --- games ---
    games_p = subparsers.add_parser("games", help="Manage tracked games")
    games_sub = games_p.add_subparsers(dest="games_cmd", required=True)

    g_list = games_sub.add_parser("list", help="List tracked games")
    g_list.set_defaults(func=cmd_games_list)

    g_add = games_sub.add_parser("add", help="Manually add a game")
    g_add.add_argument("app_id", type=int, help="Steam app ID")
    g_add.add_argument("name", help="Game name")
    g_add.add_argument("--notes", default="", help="Personal notes")
    g_add.set_defaults(func=cmd_games_add)

    g_rm = games_sub.add_parser("remove", help="Remove a tracked game")
    g_rm.add_argument("app_id", type=int, help="Steam app ID")
    g_rm.set_defaults(func=cmd_games_remove)

    g_import = games_sub.add_parser(
        "import", help="Import owned games from Steam"
    )
    g_import.add_argument("steam_id", help="Steam 64-bit user ID")
    g_import.set_defaults(func=cmd_games_import)

    # --- scrape ---
    scrape_p = subparsers.add_parser(
        "scrape", help="Scrape achievement stats from Steam"
    )
    scrape_p.add_argument("steam_id", help="Steam 64-bit user ID")
    scrape_p.add_argument(
        "app_ids",
        nargs="*",
        type=int,
        metavar="APP_ID",
        help="Specific app IDs to scrape (default: all tracked games)",
    )
    scrape_p.set_defaults(func=cmd_scrape)

    # --- analyse ---
    analyse_p = subparsers.add_parser(
        "analyse", help="Analyse stored stats for a Steam account"
    )
    analyse_p.add_argument("steam_id", help="Steam 64-bit user ID")
    analyse_p.add_argument(
        "--top-n",
        dest="top_n",
        type=int,
        default=5,
        help="Number of top entries to show (default: 5)",
    )
    analyse_p.set_defaults(func=cmd_analyse)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 1
    func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
