"""Tests for frm_client module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from frm_client import FRMClient, ChatMessage, Player, PowerStats


class TestFRMClientInit:
    """Tests for FRMClient initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        client = FRMClient(
            api_url="http://localhost:8082",
            access_token="test-token",
        )

        assert client.api_url == "http://localhost:8082"
        assert client.access_token == "test-token"
        assert client.last_timestamp == 0.0
        assert client._is_online is False
        assert client._last_error == ""

    def test_init_strips_trailing_slash(self):
        """Test trailing slash is stripped from URL."""
        client = FRMClient(
            api_url="http://localhost:8082/",
            access_token="test-token",
        )

        assert client.api_url == "http://localhost:8082"


class TestFRMClientOnlineStatus:
    """Tests for FRMClient online status tracking."""

    def test_is_online_property(self):
        """Test is_online property."""
        client = FRMClient("http://localhost:8082", "token")

        assert client.is_online is False
        client._is_online = True
        assert client.is_online is True

    def test_last_error_property(self):
        """Test last_error property."""
        client = FRMClient("http://localhost:8082", "token")

        assert client.last_error == ""
        client._last_error = "Test error"
        assert client.last_error == "Test error"

    def test_set_online_transitions(self):
        """Test online status transitions are logged."""
        client = FRMClient("http://localhost:8082", "token")

        # Going online
        client._set_online(True)
        assert client._is_online is True

        # Going offline
        client._set_online(False, "Connection lost")
        assert client._is_online is False
        assert client._last_error == "Connection lost"

        # Going back online
        client._set_online(True)
        assert client._is_online is True
        assert client._last_error == ""


class TestFRMClientGet:
    """Tests for FRMClient._get() method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp session."""
        session = AsyncMock(spec=aiohttp.ClientSession)
        session.closed = False
        return session

    async def test_get_success(self, mock_session):
        """Test successful GET request."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = mock_session

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.raise_for_status = MagicMock()

        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await client._get("testEndpoint")

        assert result == {"data": "test"}
        assert client._is_online is True

    async def test_get_connection_error(self, mock_session):
        """Test connection error handling."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = mock_session
        client._is_online = True

        mock_session.get = MagicMock(side_effect=aiohttp.ClientConnectorError(
            MagicMock(), OSError("Connection refused")
        ))

        result = await client._get("testEndpoint")

        assert result is None
        assert client._is_online is False
        assert "Cannot connect" in client._last_error

    async def test_get_timeout(self, mock_session):
        """Test timeout handling."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = mock_session
        client._is_online = True

        mock_session.get = MagicMock(side_effect=TimeoutError())

        result = await client._get("testEndpoint")

        assert result is None
        assert client._is_online is False
        assert "timeout" in client._last_error.lower()

    async def test_get_client_error(self, mock_session):
        """Test client error handling."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = mock_session
        client._is_online = True

        mock_session.get = MagicMock(side_effect=aiohttp.ClientError("Server error"))

        result = await client._get("testEndpoint")

        assert result is None
        assert client._is_online is False


class TestFRMClientGetChatMessages:
    """Tests for FRMClient.get_chat_messages() method."""

    async def test_get_chat_messages_success(self):
        """Test successful chat message retrieval."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {
                    "TimeStamp": 1234567890,
                    "ServerTimeStamp": 100.0,
                    "Sender": "Player1",
                    "Type": "Player",
                    "Message": "Hello!",
                },
            ]

            messages = await client.get_chat_messages()

            assert len(messages) == 1
            assert messages[0].sender == "Player1"
            assert messages[0].message == "Hello!"
            assert client.last_timestamp == 100.0

    async def test_get_chat_messages_filters_old(self):
        """Test old messages are filtered by timestamp."""
        client = FRMClient("http://localhost:8082", "token")
        client.last_timestamp = 50.0

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"TimeStamp": 1, "ServerTimeStamp": 30.0, "Sender": "Old", "Type": "Player", "Message": "Old"},
                {"TimeStamp": 2, "ServerTimeStamp": 60.0, "Sender": "New", "Type": "Player", "Message": "New"},
            ]

            messages = await client.get_chat_messages()

            assert len(messages) == 1
            assert messages[0].sender == "New"

    async def test_get_chat_messages_empty_response(self):
        """Test empty response handling."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            messages = await client.get_chat_messages()

            assert messages == []

    async def test_get_chat_messages_offline(self):
        """Test handling when server is offline."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            messages = await client.get_chat_messages()

            assert messages == []


class TestFRMClientSendChatMessage:
    """Tests for FRMClient.send_chat_message() method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp session."""
        session = AsyncMock(spec=aiohttp.ClientSession)
        session.closed = False
        return session

    async def test_send_chat_message_success(self, mock_session):
        """Test successful chat message send."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = mock_session

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[{"IsSent": True}])
        mock_response.raise_for_status = MagicMock()

        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await client.send_chat_message("Hello!")

        assert result is True

    async def test_send_chat_message_with_sender(self, mock_session):
        """Test send with custom sender name."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = mock_session

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[{"IsSent": True}])
        mock_response.raise_for_status = MagicMock()

        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await client.send_chat_message("Hello!", sender="CustomSender")

        assert result is True

    async def test_send_chat_message_not_sent(self, mock_session):
        """Test handling when message is not confirmed sent."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = mock_session

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[{"IsSent": False}])
        mock_response.raise_for_status = MagicMock()

        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await client.send_chat_message("Hello!")

        assert result is False

    async def test_send_chat_message_failure(self, mock_session):
        """Test failure handling."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = mock_session

        mock_session.post = MagicMock(side_effect=aiohttp.ClientError())

        result = await client.send_chat_message("Hello!")

        assert result is False


class TestFRMClientGetPlayers:
    """Tests for FRMClient.get_players() method."""

    async def test_get_players_success(self):
        """Test successful player retrieval."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"Name": "Player1", "Id": "id1", "PingMs": 50, "Online": True},
                {"Name": "Player2", "Id": "id2", "PingMs": 100, "Online": True},
            ]

            players = await client.get_players()

            assert len(players) == 2
            assert players[0].name == "Player1"
            assert players[0].ping == 50

    async def test_get_players_filters_offline(self):
        """Test offline players are filtered."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"Name": "Online", "Id": "id1", "PingMs": 50, "Online": True},
                {"Name": "Offline", "Id": "id2", "PingMs": 0, "Online": False},
            ]

            players = await client.get_players()

            assert len(players) == 1
            assert players[0].name == "Online"

    async def test_get_players_filters_empty_names(self):
        """Test players with empty names are filtered."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"Name": "Valid", "Id": "id1", "PingMs": 50, "Online": True},
                {"Name": "", "Id": "id2", "PingMs": 50, "Online": True},
                {"Name": "   ", "Id": "id3", "PingMs": 50, "Online": True},
            ]

            players = await client.get_players()

            assert len(players) == 1
            assert players[0].name == "Valid"


class TestFRMClientGetPower:
    """Tests for FRMClient.get_power() method."""

    async def test_get_power_success(self):
        """Test successful power stats retrieval."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {
                    "PowerProduction": 1000.0,
                    "PowerConsumed": 800.0,
                    "PowerMaxConsumed": 1200.0,
                    "BatteryPercent": 75.0,
                    "BatteryCapacity": 100.0,
                    "FuseTriggered": False,
                },
            ]

            power = await client.get_power()

            assert power is not None
            assert power.total_production == 1000.0
            assert power.total_consumption == 800.0
            assert power.fuse_triggered is False

    async def test_get_power_aggregates_circuits(self):
        """Test power stats are aggregated across circuits."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"PowerProduction": 500.0, "PowerConsumed": 400.0, "PowerMaxConsumed": 600.0, "BatteryPercent": 50.0, "BatteryCapacity": 50.0, "FuseTriggered": False},
                {"PowerProduction": 500.0, "PowerConsumed": 400.0, "PowerMaxConsumed": 600.0, "BatteryPercent": 75.0, "BatteryCapacity": 50.0, "FuseTriggered": False},
            ]

            power = await client.get_power()

            assert power is not None
            assert power.total_production == 1000.0
            assert power.total_consumption == 800.0
            assert power.battery_percent == 75.0  # Max of circuits
            assert power.battery_capacity == 100.0

    async def test_get_power_fuse_triggered_any(self):
        """Test fuse_triggered is True if any circuit is tripped."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"PowerProduction": 500.0, "PowerConsumed": 400.0, "PowerMaxConsumed": 600.0, "BatteryPercent": 0, "BatteryCapacity": 0, "FuseTriggered": False},
                {"PowerProduction": 500.0, "PowerConsumed": 400.0, "PowerMaxConsumed": 600.0, "BatteryPercent": 0, "BatteryCapacity": 0, "FuseTriggered": True},
            ]

            power = await client.get_power()

            assert power is not None
            assert power.fuse_triggered is True


class TestFRMClientGetFactoryStats:
    """Tests for FRMClient.get_factory_stats() method."""

    async def test_get_factory_stats_success(self):
        """Test successful factory stats retrieval."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"IsProducing": True, "Productivity": 100.0},
                {"IsProducing": True, "Productivity": 80.0},
                {"IsProducing": False, "Productivity": 0.0},
            ]

            stats = await client.get_factory_stats()

            assert stats is not None
            assert stats["total_buildings"] == 3
            assert stats["running"] == 2
            assert stats["idle"] == 1
            assert stats["avg_efficiency"] == 60.0  # (100+80+0)/3


class TestFRMClientGetTrains:
    """Tests for FRMClient.get_trains() method."""

    async def test_get_trains_success(self):
        """Test successful train retrieval."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"Name": "Train1", "ForwardSpeed": 100, "Status": "Running", "PowerConsumed": 50},
            ]

            trains = await client.get_trains()

            assert len(trains) == 1
            assert trains[0]["name"] == "Train1"
            assert trains[0]["speed"] == 100


class TestFRMClientGetDrones:
    """Tests for FRMClient.get_drones() method."""

    async def test_get_drones_success(self):
        """Test successful drone retrieval."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"HomeStation": "Home", "PairedStation": "Dest", "CurrentFlyingMode": "Flying", "FlyingSpeed": 50},
            ]

            drones = await client.get_drones()

            assert len(drones) == 1
            assert drones[0]["home"] == "Home"
            assert drones[0]["destination"] == "Dest"


class TestFRMClientGetStorageItems:
    """Tests for FRMClient.get_storage_items() method."""

    async def test_get_storage_items_success(self):
        """Test successful storage item retrieval."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"Inventory": [{"Name": "Iron Ore", "Amount": 100}]},
                {"Inventory": [{"Name": "Iron Ore", "Amount": 50}, {"Name": "Copper Ore", "Amount": 75}]},
            ]

            items = await client.get_storage_items()

            assert len(items) == 2
            # Items should be sorted by amount descending
            assert items[0]["name"] == "Iron Ore"
            assert items[0]["amount"] == 150  # Aggregated

    async def test_get_storage_items_search(self):
        """Test storage search filtering."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"Inventory": [{"Name": "Iron Ore", "Amount": 100}, {"Name": "Copper Ore", "Amount": 50}]},
            ]

            items = await client.get_storage_items("iron")

            assert len(items) == 1
            assert items[0]["name"] == "Iron Ore"


class TestFRMClientGetSinkStats:
    """Tests for FRMClient.get_sink_stats() method."""

    async def test_get_sink_stats_success(self):
        """Test successful sink stats retrieval."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"NumCoupon": 10, "TotalPoints": 100000, "PointsToCoupon": 5000, "Percent": 0.5},
            ]

            sink = await client.get_sink_stats()

            assert sink is not None
            assert sink["coupons"] == 10
            assert sink["percent"] == 50.0


class TestFRMClientHealthCheck:
    """Tests for FRMClient.health_check() method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp session."""
        session = AsyncMock(spec=aiohttp.ClientSession)
        session.closed = False
        return session

    async def test_health_check_success(self, mock_session):
        """Test successful health check."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = mock_session

        mock_response = AsyncMock()
        mock_response.status = 200

        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await client.health_check()

        assert result is True

    async def test_health_check_failure(self, mock_session):
        """Test failed health check."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = mock_session

        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await client.health_check()

        assert result is False


class TestFRMClientInitializeTimestamp:
    """Tests for FRMClient.initialize_timestamp() method."""

    async def test_initialize_timestamp_success(self):
        """Test successful timestamp initialization."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"ServerTimeStamp": 100.0},
                {"ServerTimeStamp": 200.0},
            ]

            await client.initialize_timestamp()

            assert client.last_timestamp == 200.0

    async def test_initialize_timestamp_empty(self):
        """Test timestamp initialization with no messages."""
        client = FRMClient("http://localhost:8082", "token")

        with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            await client.initialize_timestamp()

            assert client.last_timestamp == 0.0


class TestDataClasses:
    """Tests for FRM data classes."""

    def test_chat_message(self):
        """Test ChatMessage dataclass."""
        msg = ChatMessage(
            timestamp=123,
            server_timestamp=100.0,
            sender="Player",
            message_type="Player",
            message="Hello",
        )

        assert msg.timestamp == 123
        assert msg.server_timestamp == 100.0
        assert msg.sender == "Player"

    def test_player(self):
        """Test Player dataclass."""
        player = Player(
            name="TestPlayer",
            player_id="id123",
            ping=50,
        )

        assert player.name == "TestPlayer"
        assert player.ping == 50

    def test_power_stats(self):
        """Test PowerStats dataclass."""
        stats = PowerStats(
            total_production=1000.0,
            total_consumption=800.0,
            max_consumption=1200.0,
            battery_percent=75.0,
            battery_capacity=100.0,
            fuse_triggered=False,
        )

        assert stats.total_production == 1000.0
        assert stats.fuse_triggered is False
