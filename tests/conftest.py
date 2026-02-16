"""Pytest fixtures and configuration for satisfactory-signal tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from config import Config
from frm_client import FRMClient, ChatMessage, Player, PowerStats
from signal_client import SignalClient, SignalMessage
from server_api_client import ServerAPIClient, SessionInfo
from text_processing import Attachment, Mention


@pytest.fixture
def sample_config():
    """Return a sample configuration for testing."""
    return Config(
        signal_api_url="http://localhost:8080",
        signal_phone_number="+1234567890",
        signal_group_id="group.dGVzdGdyb3VwaWQ=",
        signal_recipients=[],
        frm_api_url="http://localhost:8082",
        frm_access_token="test-token",
        server_api_url="https://localhost:7777",
        server_api_token="server-token",
        poll_interval=2.0,
        log_level="INFO",
        bot_name="TestBot",
        server_host="game.example.com",
        server_port=7777,
        server_password="secret",
    )


@pytest.fixture
def mock_signal_client():
    """Return a mocked SignalClient."""
    with patch.object(SignalClient, '__init__', lambda self, *args, **kwargs: None):
        client = SignalClient.__new__(SignalClient)
        client.api_url = "http://localhost:8080"
        client.phone_number = "+1234567890"
        client.group_id = "group.dGVzdGdyb3VwaWQ="
        client._internal_group_id = "testgroupid"
        client._ws_url = "ws://localhost:8080"
        client._client = AsyncMock()
        return client


@pytest.fixture
def mock_frm_client():
    """Return a mocked FRMClient."""
    with patch.object(FRMClient, '__init__', lambda self, *args, **kwargs: None):
        client = FRMClient.__new__(FRMClient)
        client.api_url = "http://localhost:8082"
        client.access_token = "test-token"
        client.timeout = 10.0
        client.last_timestamp = 0.0
        client._client = AsyncMock()
        client._is_online = True
        client._last_error = ""
        return client


@pytest.fixture
def mock_server_client():
    """Return a mocked ServerAPIClient."""
    with patch.object(ServerAPIClient, '__init__', lambda self, *args, **kwargs: None):
        client = ServerAPIClient.__new__(ServerAPIClient)
        client.api_url = "https://localhost:7777"
        client.api_token = "test-token"
        client._client = AsyncMock()
        return client


@pytest.fixture
def sample_signal_message():
    """Return a sample SignalMessage for testing."""
    return SignalMessage(
        sender="TestUser",
        sender_uuid="test-uuid-1234",
        text="Hello, world!",
        timestamp=1234567890000,
        group_id="testgroupid",
        is_group=True,
        attachments=[],
        has_sticker=False,
        mentions=[],
    )


@pytest.fixture
def sample_chat_message():
    """Return a sample ChatMessage for testing."""
    return ChatMessage(
        timestamp=1234567890,
        server_timestamp=12345.67890,
        sender="GamePlayer",
        message_type="Player",
        message="Hello from the game!",
    )


@pytest.fixture
def sample_player():
    """Return a sample Player for testing."""
    return Player(
        name="TestPlayer",
        player_id="player-123",
        ping=50,
    )


@pytest.fixture
def sample_power_stats():
    """Return sample PowerStats for testing."""
    return PowerStats(
        total_production=1500.0,
        total_consumption=1200.0,
        max_consumption=1800.0,
        battery_percent=75.0,
        battery_capacity=100.0,
        fuse_triggered=False,
    )


@pytest.fixture
def sample_session_info():
    """Return sample SessionInfo for testing."""
    return SessionInfo(
        session_name="Test Session",
        players_online=2,
        player_limit=4,
        tech_tier=5,
        game_phase="Phase 3 (2/3 deliveries)",
        total_playtime_seconds=36000,
        tick_rate=30.0,
        is_paused=False,
        active_schematic="None",
    )


@pytest.fixture
def sample_attachment():
    """Return a sample Attachment for testing."""
    return Attachment(
        content_type="image/jpeg",
        filename="photo.jpg",
        size=1024,
        id="attachment-123",
    )


@pytest.fixture
def sample_mention():
    """Return a sample Mention for testing."""
    return Mention(
        start=0,
        length=1,
        name="MentionedUser",
        uuid="mention-uuid-123",
    )
