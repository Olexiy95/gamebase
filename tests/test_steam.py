"""Tests for gamebase.steam (SteamClient)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from gamebase.steam import SteamAPIError, SteamClient


class TestSteamClientInit:
    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError):
            SteamClient("")


class TestSteamClientGetPlayerSummary:
    def _client(self) -> SteamClient:
        return SteamClient("fake_key")

    def test_returns_player_data(self):
        client = self._client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "response": {
                "players": [
                    {
                        "steamid": "76561198000000001",
                        "personaname": "Alice",
                        "profileurl": "https://steamcommunity.com/id/alice/",
                        "avatarfull": "https://example.com/avatar.jpg",
                        "realname": "Alice Smith",
                        "loccountrycode": "US",
                    }
                ]
            }
        }
        mock_resp.raise_for_status = MagicMock()
        with patch.object(client._session, "get", return_value=mock_resp):
            result = client.get_player_summary("76561198000000001")
        assert result["personaname"] == "Alice"

    def test_missing_player_raises(self):
        client = self._client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": {"players": []}}
        mock_resp.raise_for_status = MagicMock()
        with patch.object(client._session, "get", return_value=mock_resp):
            with pytest.raises(SteamAPIError):
                client.get_player_summary("76561198000000001")


class TestSteamClientGetOwnedGames:
    def _client(self) -> SteamClient:
        return SteamClient("fake_key")

    def test_returns_games(self):
        client = self._client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "response": {
                "games": [
                    {"appid": 570, "name": "Dota 2", "playtime_forever": 600},
                    {"appid": 730, "name": "CS:GO", "playtime_forever": 300},
                ]
            }
        }
        mock_resp.raise_for_status = MagicMock()
        with patch.object(client._session, "get", return_value=mock_resp):
            games = client.get_owned_games("76561198000000001")
        assert len(games) == 2
        assert games[0]["name"] == "Dota 2"


class TestSteamClientGetAchievements:
    def _client(self) -> SteamClient:
        return SteamClient("fake_key")

    def test_returns_achievements(self):
        client = self._client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "playerstats": {
                "success": True,
                "achievements": [
                    {"apiname": "ACH1", "name": "First", "achieved": 1, "unlocktime": 0},
                    {"apiname": "ACH2", "name": "Second", "achieved": 0, "unlocktime": 0},
                ],
            }
        }
        mock_resp.raise_for_status = MagicMock()
        with patch.object(client._session, "get", return_value=mock_resp):
            result = client.get_achievements("76561198000000001", 570)
        assert len(result) == 2

    def test_http_error_returns_empty(self):
        client = self._client()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError()
        with patch.object(client._session, "get", return_value=mock_resp):
            result = client.get_achievements("76561198000000001", 9999)
        assert result == []

    def test_not_success_returns_empty(self):
        client = self._client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"playerstats": {"success": False}}
        mock_resp.raise_for_status = MagicMock()
        with patch.object(client._session, "get", return_value=mock_resp):
            result = client.get_achievements("76561198000000001", 570)
        assert result == []


class TestParseLastPlayed:
    def test_none_input(self):
        assert SteamClient.parse_last_played(None) is None

    def test_zero_input(self):
        assert SteamClient.parse_last_played(0) is None

    def test_valid_timestamp(self):
        result = SteamClient.parse_last_played(1609459200)  # 2021-01-01 00:00:00 UTC
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
