# gamebase

Game tracking, Steam account management, stats scraping and analysis.

## Features

- **Game Tracker** – add, update, list and remove games from a local SQLite database
- **Steam Account Keeper** – store and refresh Steam player profiles
- **Stats Scraper** – fetch owned games, achievements and numeric stats via the Steam Web API
- **Stats Analyser** – derive insights: top-played games, completion rates, unplayed games, and more

## Requirements

- Python ≥ 3.10
- `requests` (installed automatically)
- A [Steam Web API key](https://steamcommunity.com/dev/apikey) for scraping

## Installation

```bash
pip install -e .
```

## Quick start

```bash
# Set your Steam API key
export STEAM_API_KEY=your_key_here

# Add a Steam account (fetches profile from Steam)
gamebase account add 76561198000000000

# Import all owned games for that account
gamebase games import 76561198000000000

# Scrape achievement stats for all tracked games
gamebase scrape 76561198000000000

# Analyse the library
gamebase analyse 76561198000000000

# List tracked games
gamebase games list
```

## CLI reference

```
gamebase [--db PATH] [--api-key KEY] <command>

Commands:
  account add <steam_id>       Add/refresh a Steam account
  account list                 List stored Steam accounts
  account remove <steam_id>    Remove a Steam account

  games list                   List tracked games (ordered by playtime)
  games add <app_id> <name>    Manually add a game
  games remove <app_id>        Remove a tracked game
  games import <steam_id>      Import owned games from Steam

  scrape <steam_id> [app_ids…] Scrape achievement stats from Steam
  analyse <steam_id>           Show library summary and top lists
```

The database is stored at `~/.gamebase/gamebase.db` by default. Override with `--db PATH`.

## Running tests

```bash
pip install pytest
pytest
```
