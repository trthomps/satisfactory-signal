"""Tests for server_api_client module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from server_api_client import ServerAPIClient, SessionInfo


class TestServerAPIClientInit:
    """Tests for ServerAPIClient initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        client = ServerAPIClient(
            api_url="https://localhost:7777",
            api_token="test-token",
        )

        assert client.api_url == "https://localhost:7777"
        assert client.api_token == "test-token"

    def test_init_strips_trailing_slash(self):
        """Test trailing slash is stripped from URL."""
        client = ServerAPIClient(
            api_url="https://localhost:7777/",
            api_token="test-token",
        )

        assert client.api_url == "https://localhost:7777"

    def test_init_sets_ssl_context(self):
        """Test SSL context is set to not verify."""
        client = ServerAPIClient(
            api_url="https://localhost:7777",
            api_token="test-token",
        )

        # SSL context should be set to not verify certificates
        assert client._ssl_context is not None


class TestServerAPIClientCall:
    """Tests for ServerAPIClient._call() method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp session."""
        session = AsyncMock(spec=aiohttp.ClientSession)
        session.closed = False
        return session

    async def test_call_success(self, mock_session):
        """Test successful API call."""
        client = ServerAPIClient("https://localhost:7777", "token")
        client._session = mock_session

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"data": {"result": "success"}})
        mock_response.raise_for_status = MagicMock()

        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await client._call("TestFunction")

        assert result == {"result": "success"}

    async def test_call_with_data(self, mock_session):
        """Test API call with data parameter."""
        client = ServerAPIClient("https://localhost:7777", "token")
        client._session = mock_session

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"data": {}})
        mock_response.raise_for_status = MagicMock()

        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        await client._call("TestFunction", data={"key": "value"})

        # Verify post was called
        mock_session.post.assert_called_once()

    async def test_call_failure(self, mock_session):
        """Test API call failure handling."""
        client = ServerAPIClient("https://localhost:7777", "token")
        client._session = mock_session
        mock_session.post = MagicMock(side_effect=aiohttp.ClientError())

        result = await client._call("TestFunction")

        assert result is None


class TestServerAPIClientGetSessionInfo:
    """Tests for ServerAPIClient.get_session_info() method."""

    async def test_get_session_info_success(self):
        """Test successful session info retrieval."""
        client = ServerAPIClient("https://localhost:7777", "token")

        with patch.object(client, '_call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "serverGameState": {
                    "activeSessionName": "Test Session",
                    "numConnectedPlayers": 2,
                    "playerLimit": 4,
                    "techTier": 5,
                    "gamePhase": "/Game/FactoryGame/GamePhases/GP_Project_Assembly_Phase_3.GP_Project_Assembly_Phase_3",
                    "totalGameDuration": 36000,
                    "averageTickRate": 30.0,
                    "isGamePaused": False,
                    "activeSchematic": "None",
                }
            }

            info = await client.get_session_info()

            assert info is not None
            assert info.session_name == "Test Session"
            assert info.players_online == 2
            assert info.tech_tier == 5
            assert info.game_phase == "Phase 3 (2/3 deliveries)"
            assert info.tick_rate == 30.0

    async def test_get_session_info_failure(self):
        """Test session info retrieval failure."""
        client = ServerAPIClient("https://localhost:7777", "token")

        with patch.object(client, '_call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = None

            info = await client.get_session_info()

            assert info is None


class TestServerAPIClientParseGamePhase:
    """Tests for ServerAPIClient._parse_game_phase() method."""

    def test_parse_phase_1(self):
        """Test Phase 1 parsing."""
        client = ServerAPIClient("https://localhost:7777", "token")

        result = client._parse_game_phase("Phase_1")
        assert result == "Phase 1 (0/1 deliveries)"

    def test_parse_phase_2(self):
        """Test Phase 2 parsing."""
        client = ServerAPIClient("https://localhost:7777", "token")

        result = client._parse_game_phase("Phase_2")
        assert result == "Phase 2 (1/2 deliveries)"

    def test_parse_phase_3(self):
        """Test Phase 3 parsing."""
        client = ServerAPIClient("https://localhost:7777", "token")

        result = client._parse_game_phase("/Game/FactoryGame/GamePhases/GP_Project_Assembly_Phase_3.GP_Project_Assembly_Phase_3")
        assert result == "Phase 3 (2/3 deliveries)"

    def test_parse_phase_4(self):
        """Test Phase 4 parsing."""
        client = ServerAPIClient("https://localhost:7777", "token")

        result = client._parse_game_phase("Phase_4")
        assert result == "Phase 4 (3/4 deliveries)"

    def test_parse_phase_5(self):
        """Test Phase 5 parsing."""
        client = ServerAPIClient("https://localhost:7777", "token")

        result = client._parse_game_phase("Phase_5")
        assert result == "Phase 5 (4/5 deliveries)"

    def test_parse_victory(self):
        """Test Victory phase parsing."""
        client = ServerAPIClient("https://localhost:7777", "token")

        result = client._parse_game_phase("Victory")
        assert result == "Complete!"

        result = client._parse_game_phase("Phase_6")
        assert result == "Complete!"

    def test_parse_unknown(self):
        """Test unknown phase parsing."""
        client = ServerAPIClient("https://localhost:7777", "token")

        result = client._parse_game_phase("")
        assert result == "Unknown"

        result = client._parse_game_phase("SomeOtherPhase")
        assert result == "Unknown"


class TestServerAPIClientGetServerOptions:
    """Tests for ServerAPIClient.get_server_options() method."""

    async def test_get_server_options_success(self):
        """Test successful server options retrieval."""
        client = ServerAPIClient("https://localhost:7777", "token")

        with patch.object(client, '_call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "serverOptions": {
                    "FG.DSAutoPause": "True",
                    "FG.DSAutoSaveOnDisconnect": "False",
                    "FG.AutosaveInterval": "300",
                    "FG.DisableSeasonalEvents": "False",
                    "FG.NetworkQuality": "3",
                    "FG.SendGameplayData": "False",
                }
            }

            options = await client.get_server_options()

            assert options is not None
            assert options["auto_pause"] is True
            assert options["autosave_on_disconnect"] is False
            assert options["autosave_interval"] == 300
            assert options["seasonal_events"] is True  # DisableSeasonalEvents is False
            assert options["network_quality"] == 3

    async def test_get_server_options_failure(self):
        """Test server options retrieval failure."""
        client = ServerAPIClient("https://localhost:7777", "token")

        with patch.object(client, '_call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = None

            options = await client.get_server_options()

            assert options is None


class TestServerAPIClientGetAdvancedSettings:
    """Tests for ServerAPIClient.get_advanced_settings() method."""

    async def test_get_advanced_settings_success(self):
        """Test successful advanced settings retrieval."""
        client = ServerAPIClient("https://localhost:7777", "token")

        with patch.object(client, '_call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "creativeModeEnabled": True,
                "advancedGameSettings": {
                    "FG.GameRules.DisableArachnidCreatures": "True",
                    "FG.PlayerRules.FlightMode": "False",
                    "FG.PlayerRules.GodMode": "True",
                    "FG.PlayerRules.NoBuildCost": "False",
                    "FG.GameRules.NoFuelCost": "False",
                    "FG.GameRules.NoPower": "False",
                    "FG.GameRules.NoUnlockCost": "False",
                    "FG.GameRules.GiveAllTiers": "False",
                    "FG.GameRules.UnlockAllResearchSchematics": "False",
                    "FG.GameRules.UnlockInstantAltRecipes": "False",
                }
            }

            settings = await client.get_advanced_settings()

            assert settings is not None
            assert settings["creative_mode"] is True
            assert settings["no_arachnids"] is True
            assert settings["god_mode"] is True
            assert settings["flight_mode"] is False

    async def test_get_advanced_settings_failure(self):
        """Test advanced settings retrieval failure."""
        client = ServerAPIClient("https://localhost:7777", "token")

        with patch.object(client, '_call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = None

            settings = await client.get_advanced_settings()

            assert settings is None


class TestServerAPIClientGetSaves:
    """Tests for ServerAPIClient.get_saves() method."""

    async def test_get_saves_success(self):
        """Test successful saves retrieval."""
        client = ServerAPIClient("https://localhost:7777", "token")

        with patch.object(client, '_call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "currentSessionIndex": 0,
                "sessions": [
                    {
                        "sessionName": "Session1",
                        "saveHeaders": [
                            {
                                "saveName": "Save1",
                                "playDurationSeconds": 3600,
                                "saveDateTime": "2026.02.03-10.30.00",
                                "isModdedSave": False,
                            },
                        ],
                    },
                ],
            }

            saves = await client.get_saves()

            assert len(saves) == 1
            assert saves[0]["name"] == "Save1"
            assert saves[0]["session"] == "Session1"
            assert saves[0]["is_current_session"] is True

    async def test_get_saves_respects_limit(self):
        """Test saves retrieval respects limit parameter."""
        client = ServerAPIClient("https://localhost:7777", "token")

        with patch.object(client, '_call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "currentSessionIndex": 0,
                "sessions": [
                    {
                        "sessionName": "Session1",
                        "saveHeaders": [
                            {"saveName": f"Save{i}", "playDurationSeconds": 3600, "saveDateTime": "", "isModdedSave": False}
                            for i in range(10)
                        ],
                    },
                ],
            }

            saves = await client.get_saves(limit=3)

            assert len(saves) == 3

    async def test_get_saves_failure(self):
        """Test saves retrieval failure."""
        client = ServerAPIClient("https://localhost:7777", "token")

        with patch.object(client, '_call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = None

            saves = await client.get_saves()

            assert saves == []


class TestServerAPIClientHealthCheck:
    """Tests for ServerAPIClient.health_check() method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp session."""
        session = AsyncMock(spec=aiohttp.ClientSession)
        session.closed = False
        return session

    async def test_health_check_success(self, mock_session):
        """Test successful health check."""
        client = ServerAPIClient("https://localhost:7777", "token")
        client._session = mock_session

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": {"health": "healthy"}})

        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await client.health_check()

        assert result is True

    async def test_health_check_unhealthy(self, mock_session):
        """Test unhealthy response."""
        client = ServerAPIClient("https://localhost:7777", "token")
        client._session = mock_session

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": {"health": "unhealthy"}})

        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await client.health_check()

        assert result is False

    async def test_health_check_wrong_status(self, mock_session):
        """Test non-200 status code."""
        client = ServerAPIClient("https://localhost:7777", "token")
        client._session = mock_session

        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await client.health_check()

        assert result is False

    async def test_health_check_exception(self, mock_session):
        """Test health check with exception."""
        client = ServerAPIClient("https://localhost:7777", "token")
        client._session = mock_session
        mock_session.post = MagicMock(side_effect=Exception("Connection failed"))

        result = await client.health_check()

        assert result is False


class TestSessionInfo:
    """Tests for SessionInfo dataclass."""

    def test_session_info_creation(self):
        """Test SessionInfo creation."""
        info = SessionInfo(
            session_name="Test",
            players_online=2,
            player_limit=4,
            tech_tier=5,
            game_phase="Phase 3",
            total_playtime_seconds=3600,
            tick_rate=30.0,
            is_paused=False,
            active_schematic="None",
        )

        assert info.session_name == "Test"
        assert info.players_online == 2
        assert info.tick_rate == 30.0

    def test_session_info_equality(self):
        """Test SessionInfo equality."""
        info1 = SessionInfo("A", 1, 4, 1, "P1", 100, 30.0, False, "None")
        info2 = SessionInfo("A", 1, 4, 1, "P1", 100, 30.0, False, "None")
        info3 = SessionInfo("B", 1, 4, 1, "P1", 100, 30.0, False, "None")

        assert info1 == info2
        assert info1 != info3
