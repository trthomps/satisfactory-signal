"""Tests for frm_client module."""

from unittest.mock import MagicMock

import requests

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

    def test_timestamp_reinitialized_on_reconnect(self):
        """Test that timestamp is reinitialized when server comes back online."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        # Set up mock response for getChatMessages
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"ServerTimeStamp": 100.0, "Message": "test1"},
            {"ServerTimeStamp": 200.0, "Message": "test2"},
        ]
        client._session.get.return_value = mock_response

        # Set initial state: was online with old timestamp
        client._is_online = True
        client.last_timestamp = 5000.0  # Old high timestamp

        # Server goes offline
        client._set_online(False, "Connection lost")
        assert client.last_timestamp == 5000.0  # Timestamp unchanged

        # Server comes back online - timestamp should reinitialize
        client._set_online(True)
        assert client.last_timestamp == 200.0  # Should be max from new messages

    def test_timestamp_reinitialized_to_zero_on_empty_messages(self):
        """Test timestamp resets to 0 when server returns no messages."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        # Set up mock response with empty messages
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        client._session.get.return_value = mock_response

        # Set initial state
        client._is_online = True
        client.last_timestamp = 5000.0

        # Server goes offline then back online
        client._set_online(False)
        client._set_online(True)

        assert client.last_timestamp == 0.0


class TestFRMClientGet:
    """Tests for FRMClient._get() method."""

    def test_get_success(self):
        """Test successful GET request."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()
        client._is_online = True  # Already online to avoid reinitialize call

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        result = client._get("testEndpoint")

        assert result == {"data": "test"}
        assert client._is_online is True
        client._session.get.assert_called_with(
            "http://localhost:8082/testEndpoint",
            timeout=5,
        )

    def test_get_connection_error(self):
        """Test connection error handling."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()
        client._is_online = True

        client._session.get.side_effect = requests.ConnectionError()

        result = client._get("testEndpoint")

        assert result is None
        assert client._is_online is False
        assert "Cannot connect" in client._last_error

    def test_get_timeout(self):
        """Test timeout handling."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()
        client._is_online = True

        client._session.get.side_effect = requests.Timeout()

        result = client._get("testEndpoint")

        assert result is None
        assert client._is_online is False
        assert "timeout" in client._last_error.lower()

    def test_get_request_error(self):
        """Test request error handling."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()
        client._is_online = True

        client._session.get.side_effect = requests.RequestException("Server error")

        result = client._get("testEndpoint")

        assert result is None
        assert client._is_online is False


class TestFRMClientGetChatMessages:
    """Tests for FRMClient.get_chat_messages() method."""

    def test_get_chat_messages_success(self):
        """Test successful chat message retrieval."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "TimeStamp": 1234567890,
                "ServerTimeStamp": 100.0,
                "Sender": "Player1",
                "Type": "Player",
                "Message": "Hello!",
            },
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        messages = client.get_chat_messages()

        assert len(messages) == 1
        assert messages[0].sender == "Player1"
        assert messages[0].message == "Hello!"
        assert client.last_timestamp == 100.0

    def test_get_chat_messages_filters_old(self):
        """Test old messages are filtered by timestamp."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()
        client.last_timestamp = 50.0

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"TimeStamp": 1, "ServerTimeStamp": 30.0, "Sender": "Old", "Type": "Player", "Message": "Old"},
            {"TimeStamp": 2, "ServerTimeStamp": 60.0, "Sender": "New", "Type": "Player", "Message": "New"},
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        messages = client.get_chat_messages()

        assert len(messages) == 1
        assert messages[0].sender == "New"

    def test_get_chat_messages_empty_response(self):
        """Test empty response handling."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        messages = client.get_chat_messages()

        assert messages == []

    def test_get_chat_messages_offline(self):
        """Test handling when server is offline."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()
        client._session.get.side_effect = requests.ConnectionError()

        messages = client.get_chat_messages()

        assert messages == []


class TestFRMClientSendChatMessage:
    """Tests for FRMClient.send_chat_message() method."""

    def test_send_chat_message_success(self):
        """Test successful chat message send."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [{"IsSent": True}]
        mock_response.raise_for_status = MagicMock()
        client._session.post.return_value = mock_response

        result = client.send_chat_message("Hello!")

        assert result is True
        call_args = client._session.post.call_args
        assert call_args[1]["json"]["message"] == "Hello!"
        assert call_args[1]["headers"]["X-FRM-Authorization"] == "token"

    def test_send_chat_message_with_sender(self):
        """Test send with custom sender name."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [{"IsSent": True}]
        mock_response.raise_for_status = MagicMock()
        client._session.post.return_value = mock_response

        result = client.send_chat_message("Hello!", sender="CustomSender")

        assert result is True
        call_args = client._session.post.call_args
        assert call_args[1]["json"]["sender"] == "CustomSender"

    def test_send_chat_message_truncates_sender(self):
        """Test sender name is truncated to 32 characters."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [{"IsSent": True}]
        mock_response.raise_for_status = MagicMock()
        client._session.post.return_value = mock_response

        long_name = "A" * 50
        result = client.send_chat_message("Hello!", sender=long_name)

        assert result is True
        call_args = client._session.post.call_args
        assert len(call_args[1]["json"]["sender"]) == 32

    def test_send_chat_message_not_sent(self):
        """Test handling when message is not confirmed sent."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [{"IsSent": False}]
        mock_response.raise_for_status = MagicMock()
        client._session.post.return_value = mock_response

        result = client.send_chat_message("Hello!")

        assert result is False

    def test_send_chat_message_failure(self):
        """Test failure handling."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()
        client._session.post.side_effect = requests.RequestException()

        result = client.send_chat_message("Hello!")

        assert result is False


class TestFRMClientGetPlayers:
    """Tests for FRMClient.get_players() method."""

    def test_get_players_success(self):
        """Test successful player retrieval."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"Name": "Player1", "Id": "id1", "PingMs": 50, "Online": True},
            {"Name": "Player2", "Id": "id2", "PingMs": 100, "Online": True},
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        players = client.get_players()

        assert len(players) == 2
        assert players[0].name == "Player1"
        assert players[0].ping == 50

    def test_get_players_filters_offline(self):
        """Test offline players are filtered."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"Name": "Online", "Id": "id1", "PingMs": 50, "Online": True},
            {"Name": "Offline", "Id": "id2", "PingMs": 0, "Online": False},
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        players = client.get_players()

        assert len(players) == 1
        assert players[0].name == "Online"

    def test_get_players_filters_empty_names(self):
        """Test players with empty names are filtered."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"Name": "Valid", "Id": "id1", "PingMs": 50, "Online": True},
            {"Name": "", "Id": "id2", "PingMs": 50, "Online": True},
            {"Name": "   ", "Id": "id3", "PingMs": 50, "Online": True},
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        players = client.get_players()

        assert len(players) == 1
        assert players[0].name == "Valid"


class TestFRMClientGetPower:
    """Tests for FRMClient.get_power() method."""

    def test_get_power_success(self):
        """Test successful power stats retrieval."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "PowerProduction": 1000.0,
                "PowerConsumed": 800.0,
                "PowerMaxConsumed": 1200.0,
                "BatteryPercent": 75.0,
                "BatteryCapacity": 100.0,
                "FuseTriggered": False,
            },
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        power = client.get_power()

        assert power is not None
        assert power.total_production == 1000.0
        assert power.total_consumption == 800.0
        assert power.fuse_triggered is False

    def test_get_power_aggregates_circuits(self):
        """Test power stats are aggregated across circuits."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"PowerProduction": 500.0, "PowerConsumed": 400.0, "PowerMaxConsumed": 600.0, "BatteryPercent": 50.0, "BatteryCapacity": 50.0, "FuseTriggered": False},
            {"PowerProduction": 500.0, "PowerConsumed": 400.0, "PowerMaxConsumed": 600.0, "BatteryPercent": 75.0, "BatteryCapacity": 50.0, "FuseTriggered": False},
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        power = client.get_power()

        assert power is not None
        assert power.total_production == 1000.0
        assert power.total_consumption == 800.0
        assert power.battery_percent == 75.0  # Max of circuits
        assert power.battery_capacity == 100.0

    def test_get_power_fuse_triggered_any(self):
        """Test fuse_triggered is True if any circuit is tripped."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"PowerProduction": 500.0, "PowerConsumed": 400.0, "PowerMaxConsumed": 600.0, "BatteryPercent": 0, "BatteryCapacity": 0, "FuseTriggered": False},
            {"PowerProduction": 500.0, "PowerConsumed": 400.0, "PowerMaxConsumed": 600.0, "BatteryPercent": 0, "BatteryCapacity": 0, "FuseTriggered": True},
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        power = client.get_power()

        assert power is not None
        assert power.fuse_triggered is True


class TestFRMClientGetFactoryStats:
    """Tests for FRMClient.get_factory_stats() method."""

    def test_get_factory_stats_success(self):
        """Test successful factory stats retrieval."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"IsProducing": True, "Productivity": 100.0},
            {"IsProducing": True, "Productivity": 80.0},
            {"IsProducing": False, "Productivity": 0.0},
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        stats = client.get_factory_stats()

        assert stats is not None
        assert stats["total_buildings"] == 3
        assert stats["running"] == 2
        assert stats["idle"] == 1
        assert stats["avg_efficiency"] == 60.0  # (100+80+0)/3


class TestFRMClientGetTrains:
    """Tests for FRMClient.get_trains() method."""

    def test_get_trains_success(self):
        """Test successful train retrieval."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"Name": "Train1", "ForwardSpeed": 100, "Status": "Running", "PowerConsumed": 50},
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        trains = client.get_trains()

        assert len(trains) == 1
        assert trains[0]["name"] == "Train1"
        assert trains[0]["speed"] == 100


class TestFRMClientGetDrones:
    """Tests for FRMClient.get_drones() method."""

    def test_get_drones_success(self):
        """Test successful drone retrieval."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"HomeStation": "Home", "PairedStation": "Dest", "CurrentFlyingMode": "Flying", "FlyingSpeed": 50},
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        drones = client.get_drones()

        assert len(drones) == 1
        assert drones[0]["home"] == "Home"
        assert drones[0]["destination"] == "Dest"


class TestFRMClientGetStorageItems:
    """Tests for FRMClient.get_storage_items() method."""

    def test_get_storage_items_success(self):
        """Test successful storage item retrieval."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"Inventory": [{"Name": "Iron Ore", "Amount": 100}]},
            {"Inventory": [{"Name": "Iron Ore", "Amount": 50}, {"Name": "Copper Ore", "Amount": 75}]},
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        items = client.get_storage_items()

        assert len(items) == 2
        # Items should be sorted by amount descending
        assert items[0]["name"] == "Iron Ore"
        assert items[0]["amount"] == 150  # Aggregated

    def test_get_storage_items_search(self):
        """Test storage search filtering."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"Inventory": [{"Name": "Iron Ore", "Amount": 100}, {"Name": "Copper Ore", "Amount": 50}]},
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        items = client.get_storage_items("iron")

        assert len(items) == 1
        assert items[0]["name"] == "Iron Ore"


class TestFRMClientGetSinkStats:
    """Tests for FRMClient.get_sink_stats() method."""

    def test_get_sink_stats_success(self):
        """Test successful sink stats retrieval."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"NumCoupon": 10, "TotalPoints": 100000, "PointsToCoupon": 5000, "Percent": 0.5},
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        sink = client.get_sink_stats()

        assert sink is not None
        assert sink["coupons"] == 10
        assert sink["percent"] == 50.0


class TestFRMClientHealthCheck:
    """Tests for FRMClient.health_check() method."""

    def test_health_check_success(self):
        """Test successful health check."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        client._session.get.return_value = mock_response

        result = client.health_check()

        assert result is True

    def test_health_check_failure(self):
        """Test failed health check."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 500
        client._session.get.return_value = mock_response

        result = client.health_check()

        assert result is False


class TestFRMClientInitializeTimestamp:
    """Tests for FRMClient.initialize_timestamp() method."""

    def test_initialize_timestamp_success(self):
        """Test successful timestamp initialization."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"ServerTimeStamp": 100.0},
            {"ServerTimeStamp": 200.0},
        ]
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        client.initialize_timestamp()

        assert client.last_timestamp == 200.0

    def test_initialize_timestamp_empty(self):
        """Test timestamp initialization with no messages."""
        client = FRMClient("http://localhost:8082", "token")
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        client._session.get.return_value = mock_response

        client.initialize_timestamp()

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
