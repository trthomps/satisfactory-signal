"""Tests for frm_client module."""

from unittest.mock import AsyncMock, MagicMock

import httpx

from frm_client import FRMClient, ChatMessage, Player, PowerStats


def _make_client(url="http://localhost:8082", token="token", timeout=10.0):
    """Create a FRMClient with a mocked async HTTP client."""
    client = FRMClient(api_url=url, access_token=token, timeout=timeout)
    mock_http = AsyncMock()
    client._client = mock_http
    return client, mock_http


def _mock_response(json_data=None, status_code=200, raise_for_status=None):
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    if raise_for_status:
        resp.raise_for_status.side_effect = raise_for_status
    else:
        resp.raise_for_status = MagicMock()
    return resp


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
        assert client.timeout == 10.0
        assert client.last_timestamp == 0.0
        assert client._is_online is False
        assert client._last_error == ""

    def test_init_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = FRMClient(
            api_url="http://localhost:8082",
            access_token="test-token",
            timeout=15.0,
        )

        assert client.timeout == 15.0

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

    async def test_set_online_transitions(self):
        """Test online status transitions are logged."""
        client, mock_http = _make_client()

        # Mock the reinitialize response for when going online
        mock_resp = _mock_response(json_data=[], status_code=200)
        mock_http.get.return_value = mock_resp

        # Going online
        await client._set_online(True)
        assert client._is_online is True

        # Going offline
        await client._set_online(False, "Connection lost")
        assert client._is_online is False
        assert client._last_error == "Connection lost"

        # Going back online
        await client._set_online(True)
        assert client._is_online is True
        assert client._last_error == ""

    async def test_timestamp_reinitialized_on_reconnect(self):
        """Test that timestamp is reinitialized when server comes back online."""
        client, mock_http = _make_client()

        # Set up mock response for getChatMessages
        mock_resp = _mock_response(
            json_data=[
                {"ServerTimeStamp": 100.0, "Message": "test1"},
                {"ServerTimeStamp": 200.0, "Message": "test2"},
            ],
            status_code=200,
        )
        mock_http.get.return_value = mock_resp

        # Set initial state: was online with old timestamp
        client._is_online = True
        client.last_timestamp = 5000.0  # Old high timestamp

        # Server goes offline
        await client._set_online(False, "Connection lost")
        assert client.last_timestamp == 5000.0  # Timestamp unchanged

        # Server comes back online - timestamp should reinitialize
        await client._set_online(True)
        assert client.last_timestamp == 200.0  # Should be max from new messages

    async def test_timestamp_reinitialized_to_zero_on_empty_messages(self):
        """Test timestamp resets to 0 when server returns no messages."""
        client, mock_http = _make_client()

        # Set up mock response with empty messages
        mock_resp = _mock_response(json_data=[], status_code=200)
        mock_http.get.return_value = mock_resp

        # Set initial state
        client._is_online = True
        client.last_timestamp = 5000.0

        # Server goes offline then back online
        await client._set_online(False)
        await client._set_online(True)

        assert client.last_timestamp == 0.0


class TestFRMClientGet:
    """Tests for FRMClient._get() method."""

    async def test_get_success(self):
        """Test successful GET request."""
        client, mock_http = _make_client()
        client._is_online = True  # Already online to avoid reinitialize call

        mock_resp = _mock_response(json_data={"data": "test"})
        mock_http.get.return_value = mock_resp

        result = await client._get("testEndpoint")

        assert result == {"data": "test"}
        assert client._is_online is True

    async def test_get_connection_error(self):
        """Test connection error handling."""
        client, mock_http = _make_client()
        client._is_online = True

        mock_http.get.side_effect = httpx.ConnectError("Connection refused")

        result = await client._get("testEndpoint")

        assert result is None
        assert client._is_online is False
        assert "Cannot connect" in client._last_error

    async def test_get_timeout(self):
        """Test timeout handling."""
        client, mock_http = _make_client()
        client._is_online = True

        mock_http.get.side_effect = httpx.TimeoutException("Timeout")

        result = await client._get("testEndpoint")

        assert result is None
        assert client._is_online is False
        assert "timeout" in client._last_error.lower()

    async def test_get_http_status_error(self):
        """Test HTTP status error handling."""
        client, mock_http = _make_client()
        client._is_online = True

        mock_resp = _mock_response(status_code=500)
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_resp,
        )
        mock_http.get.return_value = mock_resp

        result = await client._get("testEndpoint")

        assert result is None
        assert client._is_online is False


class TestFRMClientGetChatMessages:
    """Tests for FRMClient.get_chat_messages() method."""

    async def test_get_chat_messages_success(self):
        """Test successful chat message retrieval."""
        client, mock_http = _make_client()
        client._is_online = True  # Avoid reinitialize on first success

        mock_resp = _mock_response(json_data=[
            {
                "TimeStamp": 1234567890,
                "ServerTimeStamp": 100.0,
                "Sender": "Player1",
                "Type": "Player",
                "Message": "Hello!",
            },
        ])
        mock_http.get.return_value = mock_resp

        messages = await client.get_chat_messages()

        assert len(messages) == 1
        assert messages[0].sender == "Player1"
        assert messages[0].message == "Hello!"
        assert client.last_timestamp == 100.0

    async def test_get_chat_messages_filters_old(self):
        """Test old messages are filtered by timestamp."""
        client, mock_http = _make_client()
        client._is_online = True  # Avoid reinitialize on first success
        client.last_timestamp = 50.0

        mock_resp = _mock_response(json_data=[
            {"TimeStamp": 1, "ServerTimeStamp": 30.0, "Sender": "Old", "Type": "Player", "Message": "Old"},
            {"TimeStamp": 2, "ServerTimeStamp": 60.0, "Sender": "New", "Type": "Player", "Message": "New"},
        ])
        mock_http.get.return_value = mock_resp

        messages = await client.get_chat_messages()

        assert len(messages) == 1
        assert messages[0].sender == "New"

    async def test_get_chat_messages_empty_response(self):
        """Test empty response handling."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[])
        mock_http.get.return_value = mock_resp

        messages = await client.get_chat_messages()

        assert messages == []

    async def test_get_chat_messages_offline(self):
        """Test handling when server is offline."""
        client, mock_http = _make_client()
        mock_http.get.side_effect = httpx.ConnectError("Connection refused")

        messages = await client.get_chat_messages()

        assert messages == []


class TestFRMClientSendChatMessage:
    """Tests for FRMClient.send_chat_message() method."""

    async def test_send_chat_message_success(self):
        """Test successful chat message send."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[{"IsSent": True}])
        mock_http.post.return_value = mock_resp

        result = await client.send_chat_message("Hello!")

        assert result is True
        call_kwargs = mock_http.post.call_args[1]
        assert call_kwargs["json"]["message"] == "Hello!"
        assert call_kwargs["headers"]["X-FRM-Authorization"] == "token"

    async def test_send_chat_message_with_sender(self):
        """Test send with custom sender name."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[{"IsSent": True}])
        mock_http.post.return_value = mock_resp

        result = await client.send_chat_message("Hello!", sender="CustomSender")

        assert result is True
        call_kwargs = mock_http.post.call_args[1]
        assert call_kwargs["json"]["sender"] == "CustomSender"

    async def test_send_chat_message_truncates_sender(self):
        """Test sender name is truncated to 32 characters."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[{"IsSent": True}])
        mock_http.post.return_value = mock_resp

        long_name = "A" * 50
        result = await client.send_chat_message("Hello!", sender=long_name)

        assert result is True
        call_kwargs = mock_http.post.call_args[1]
        assert len(call_kwargs["json"]["sender"]) == 32

    async def test_send_chat_message_not_sent(self):
        """Test handling when message is not confirmed sent."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[{"IsSent": False}])
        mock_http.post.return_value = mock_resp

        result = await client.send_chat_message("Hello!")

        assert result is False

    async def test_send_chat_message_failure(self):
        """Test failure handling."""
        client, mock_http = _make_client()
        mock_resp = _mock_response(status_code=500)
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_resp,
        )
        mock_http.post.return_value = mock_resp

        result = await client.send_chat_message("Hello!")

        assert result is False


class TestFRMClientGetPlayers:
    """Tests for FRMClient.get_players() method."""

    async def test_get_players_success(self):
        """Test successful player retrieval."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[
            {"Name": "Player1", "Id": "id1", "PingMs": 50, "Online": True},
            {"Name": "Player2", "Id": "id2", "PingMs": 100, "Online": True},
        ])
        mock_http.get.return_value = mock_resp

        players = await client.get_players()

        assert len(players) == 2
        assert players[0].name == "Player1"
        assert players[0].ping == 50

    async def test_get_players_filters_offline(self):
        """Test offline players are filtered."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[
            {"Name": "Online", "Id": "id1", "PingMs": 50, "Online": True},
            {"Name": "Offline", "Id": "id2", "PingMs": 0, "Online": False},
        ])
        mock_http.get.return_value = mock_resp

        players = await client.get_players()

        assert len(players) == 1
        assert players[0].name == "Online"

    async def test_get_players_filters_empty_names(self):
        """Test players with empty names are filtered."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[
            {"Name": "Valid", "Id": "id1", "PingMs": 50, "Online": True},
            {"Name": "", "Id": "id2", "PingMs": 50, "Online": True},
            {"Name": "   ", "Id": "id3", "PingMs": 50, "Online": True},
        ])
        mock_http.get.return_value = mock_resp

        players = await client.get_players()

        assert len(players) == 1
        assert players[0].name == "Valid"


class TestFRMClientGetPower:
    """Tests for FRMClient.get_power() method."""

    async def test_get_power_success(self):
        """Test successful power stats retrieval."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[
            {
                "PowerProduction": 1000.0,
                "PowerConsumed": 800.0,
                "PowerMaxConsumed": 1200.0,
                "BatteryPercent": 75.0,
                "BatteryCapacity": 100.0,
                "FuseTriggered": False,
            },
        ])
        mock_http.get.return_value = mock_resp

        power = await client.get_power()

        assert power is not None
        assert power.total_production == 1000.0
        assert power.total_consumption == 800.0
        assert power.fuse_triggered is False

    async def test_get_power_aggregates_circuits(self):
        """Test power stats are aggregated across circuits."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[
            {"PowerProduction": 500.0, "PowerConsumed": 400.0, "PowerMaxConsumed": 600.0, "BatteryPercent": 50.0, "BatteryCapacity": 50.0, "FuseTriggered": False},
            {"PowerProduction": 500.0, "PowerConsumed": 400.0, "PowerMaxConsumed": 600.0, "BatteryPercent": 75.0, "BatteryCapacity": 50.0, "FuseTriggered": False},
        ])
        mock_http.get.return_value = mock_resp

        power = await client.get_power()

        assert power is not None
        assert power.total_production == 1000.0
        assert power.total_consumption == 800.0
        assert power.battery_percent == 75.0  # Max of circuits
        assert power.battery_capacity == 100.0

    async def test_get_power_fuse_triggered_any(self):
        """Test fuse_triggered is True if any circuit is tripped."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[
            {"PowerProduction": 500.0, "PowerConsumed": 400.0, "PowerMaxConsumed": 600.0, "BatteryPercent": 0, "BatteryCapacity": 0, "FuseTriggered": False},
            {"PowerProduction": 500.0, "PowerConsumed": 400.0, "PowerMaxConsumed": 600.0, "BatteryPercent": 0, "BatteryCapacity": 0, "FuseTriggered": True},
        ])
        mock_http.get.return_value = mock_resp

        power = await client.get_power()

        assert power is not None
        assert power.fuse_triggered is True


class TestFRMClientGetFactoryStats:
    """Tests for FRMClient.get_factory_stats() method."""

    async def test_get_factory_stats_success(self):
        """Test successful factory stats retrieval."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[
            {"IsProducing": True, "Productivity": 100.0},
            {"IsProducing": True, "Productivity": 80.0},
            {"IsProducing": False, "Productivity": 0.0},
        ])
        mock_http.get.return_value = mock_resp

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
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[
            {"Name": "Train1", "ForwardSpeed": 100, "Status": "Running", "PowerConsumed": 50},
        ])
        mock_http.get.return_value = mock_resp

        trains = await client.get_trains()

        assert len(trains) == 1
        assert trains[0]["name"] == "Train1"
        assert trains[0]["speed"] == 100


class TestFRMClientGetDrones:
    """Tests for FRMClient.get_drones() method."""

    async def test_get_drones_success(self):
        """Test successful drone retrieval."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[
            {"HomeStation": "Home", "PairedStation": "Dest", "CurrentFlyingMode": "Flying", "FlyingSpeed": 50},
        ])
        mock_http.get.return_value = mock_resp

        drones = await client.get_drones()

        assert len(drones) == 1
        assert drones[0]["home"] == "Home"
        assert drones[0]["destination"] == "Dest"


class TestFRMClientGetStorageItems:
    """Tests for FRMClient.get_storage_items() method."""

    async def test_get_storage_items_success(self):
        """Test successful storage item retrieval."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[
            {"Inventory": [{"Name": "Iron Ore", "Amount": 100}]},
            {"Inventory": [{"Name": "Iron Ore", "Amount": 50}, {"Name": "Copper Ore", "Amount": 75}]},
        ])
        mock_http.get.return_value = mock_resp

        items = await client.get_storage_items()

        assert len(items) == 2
        # Items should be sorted by amount descending
        assert items[0]["name"] == "Iron Ore"
        assert items[0]["amount"] == 150  # Aggregated

    async def test_get_storage_items_search(self):
        """Test storage search filtering."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[
            {"Inventory": [{"Name": "Iron Ore", "Amount": 100}, {"Name": "Copper Ore", "Amount": 50}]},
        ])
        mock_http.get.return_value = mock_resp

        items = await client.get_storage_items("iron")

        assert len(items) == 1
        assert items[0]["name"] == "Iron Ore"


class TestFRMClientGetSinkStats:
    """Tests for FRMClient.get_sink_stats() method."""

    async def test_get_sink_stats_success(self):
        """Test successful sink stats retrieval."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[
            {"NumCoupon": 10, "TotalPoints": 100000, "PointsToCoupon": 5000, "Percent": 0.5},
        ])
        mock_http.get.return_value = mock_resp

        sink = await client.get_sink_stats()

        assert sink is not None
        assert sink["coupons"] == 10
        assert sink["percent"] == 50.0


class TestFRMClientHealthCheck:
    """Tests for FRMClient.health_check() method."""

    async def test_health_check_success(self):
        """Test successful health check."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(status_code=200)
        mock_http.get.return_value = mock_resp

        result = await client.health_check()

        assert result is True

    async def test_health_check_failure(self):
        """Test failed health check."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(status_code=500)
        mock_http.get.return_value = mock_resp

        result = await client.health_check()

        assert result is False


class TestFRMClientInitializeTimestamp:
    """Tests for FRMClient.initialize_timestamp() method."""

    async def test_initialize_timestamp_success(self):
        """Test successful timestamp initialization."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[
            {"ServerTimeStamp": 100.0},
            {"ServerTimeStamp": 200.0},
        ])
        mock_http.get.return_value = mock_resp

        await client.initialize_timestamp()

        assert client.last_timestamp == 200.0

    async def test_initialize_timestamp_empty(self):
        """Test timestamp initialization with no messages."""
        client, mock_http = _make_client()

        mock_resp = _mock_response(json_data=[])
        mock_http.get.return_value = mock_resp

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
