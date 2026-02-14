"""Tests for Bridge join/leave debounce logic."""

import time
from unittest.mock import MagicMock, patch

import pytest

from config import Config
from frm_client import ChatMessage, FRMClient, Player
from main import Bridge, _DEBOUNCE_SECONDS
from signal_client import SignalClient


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config(
        signal_phone_number="+1234567890",
        signal_group_id="group.test",
        frm_access_token="token",
    )


@pytest.fixture
def bridge(config):
    """Create a Bridge with mocked clients."""
    with patch.object(SignalClient, "__init__", lambda self, *a, **kw: None), \
         patch.object(FRMClient, "__init__", lambda self, *a, **kw: None):
        b = Bridge(config)
        b.signal_client = MagicMock(spec=SignalClient)
        b.signal_client.send_to_group = MagicMock(return_value=True)
        b.frm_client = MagicMock(spec=FRMClient)
        b.frm_client.is_online = True
        return b


def _make_players(*names, dead=False):
    """Helper to create a list of Player objects."""
    return [
        Player(name=n, player_id=f"id-{n}", ping=10, dead=dead)
        for n in names
    ]


class TestIsSystemJoinLeave:
    """Tests for Bridge._is_system_join_leave()."""

    def test_left_the_game(self):
        assert Bridge._is_system_join_leave("PlayerName has left the game!")

    def test_joined_the_game(self):
        assert Bridge._is_system_join_leave("PlayerName has joined the game!")

    def test_entered_the_game(self):
        assert Bridge._is_system_join_leave("PlayerName has entered the game!")

    def test_placeholder_left(self):
        assert Bridge._is_system_join_leave("<PlayerName/> has left the game!")

    def test_case_insensitive(self):
        assert Bridge._is_system_join_leave("PlayerName Has Left The Game!")

    def test_server_save_not_matched(self):
        assert not Bridge._is_system_join_leave("Server saved the game")

    def test_autosave_not_matched(self):
        assert not Bridge._is_system_join_leave("Autosave complete")

    def test_regular_chat_not_matched(self):
        assert not Bridge._is_system_join_leave("Hello everyone!")

    def test_empty_string_not_matched(self):
        assert not Bridge._is_system_join_leave("")

    def test_no_has_prefix_not_matched(self):
        """'left the game' without 'has' should not match."""
        assert not Bridge._is_system_join_leave("I left the game early")


class TestDebounceJoinLeave:
    """Tests for debounced join/leave announcements in poll_player_events()."""

    @pytest.mark.asyncio
    async def test_camera_mode_no_announcement(self, bridge):
        """Player leaves then returns within 60s (camera mode) -> no announcements."""
        # Initialize with player online
        bridge.frm_client.get_players.return_value = _make_players("Alice")
        await bridge.poll_player_events()
        assert bridge._players_initialized

        # Player goes offline (camera mode)
        bridge.frm_client.get_players.return_value = []
        await bridge.poll_player_events()

        # Should have a pending leave, no announcement yet
        assert "Alice" in bridge._pending_leaves
        bridge.signal_client.send_to_group.assert_not_called()

        # Player comes back (camera mode return)
        bridge.frm_client.get_players.return_value = _make_players("Alice")
        await bridge.poll_player_events()

        # Pending leave cancelled, no join announcement either
        assert "Alice" not in bridge._pending_leaves
        assert "Alice" not in bridge._pending_joins
        bridge.signal_client.send_to_group.assert_not_called()

    @pytest.mark.asyncio
    async def test_real_leave_timeout(self, bridge):
        """Player leaves and doesn't return within 60s -> announce on timeout."""
        # Initialize with player online
        bridge.frm_client.get_players.return_value = _make_players("Bob")
        await bridge.poll_player_events()

        # Player goes offline
        bridge.frm_client.get_players.return_value = []
        await bridge.poll_player_events()

        assert "Bob" in bridge._pending_leaves
        bridge.signal_client.send_to_group.assert_not_called()

        # Simulate 60s passing
        bridge._pending_leaves["Bob"] = time.monotonic() - _DEBOUNCE_SECONDS - 1
        bridge.frm_client.get_players.return_value = []
        await bridge.poll_player_events()

        bridge.signal_client.send_to_group.assert_called_once_with(
            "[Server] Bob left the game"
        )
        assert "Bob" not in bridge._pending_leaves

    @pytest.mark.asyncio
    async def test_real_join_timeout(self, bridge):
        """New player joins and System message missed -> announce on timeout."""
        # Initialize with no players
        bridge.frm_client.get_players.return_value = []
        await bridge.poll_player_events()

        # New player joins
        bridge.frm_client.get_players.return_value = _make_players("Charlie")
        await bridge.poll_player_events()

        assert "Charlie" in bridge._pending_joins
        bridge.signal_client.send_to_group.assert_not_called()

        # Simulate 60s passing
        bridge._pending_joins["Charlie"] = time.monotonic() - _DEBOUNCE_SECONDS - 1
        bridge.frm_client.get_players.return_value = _make_players("Charlie")
        await bridge.poll_player_events()

        bridge.signal_client.send_to_group.assert_called_once_with(
            "[Server] Charlie joined the game"
        )
        assert "Charlie" not in bridge._pending_joins

    @pytest.mark.asyncio
    async def test_death_still_immediate(self, bridge):
        """Death announcements are not debounced."""
        # Initialize with player alive
        bridge.frm_client.get_players.return_value = _make_players("Dave")
        await bridge.poll_player_events()

        # Player dies
        bridge.frm_client.get_players.return_value = _make_players("Dave", dead=True)
        await bridge.poll_player_events()

        bridge.signal_client.send_to_group.assert_called_once_with(
            "[Server] Dave died"
        )

    @pytest.mark.asyncio
    async def test_new_join_not_in_pending_leaves(self, bridge):
        """A truly new player (not returning from camera mode) creates a pending join."""
        bridge.frm_client.get_players.return_value = []
        await bridge.poll_player_events()

        bridge.frm_client.get_players.return_value = _make_players("Eve")
        await bridge.poll_player_events()

        assert "Eve" in bridge._pending_joins
        assert "Eve" not in bridge._pending_leaves


class TestSystemMessageConfirmation:
    """Tests for System messages confirming pending events in poll_game_chat()."""

    @pytest.mark.asyncio
    async def test_system_leave_confirms_pending(self, bridge):
        """System leave message confirms a pending leave -> immediate announce."""
        bridge._pending_leaves["Alice"] = time.monotonic()

        bridge.frm_client.get_chat_messages.return_value = [
            ChatMessage(
                timestamp=1, server_timestamp=100.0,
                sender="Alice", message_type="System",
                message="<PlayerName/> has left the game!",
            ),
        ]

        await bridge.poll_game_chat()

        bridge.signal_client.send_to_group.assert_called_once_with(
            "[Server] Alice left the game"
        )
        assert "Alice" not in bridge._pending_leaves

    @pytest.mark.asyncio
    async def test_system_join_confirms_pending(self, bridge):
        """System join message confirms a pending join -> immediate announce."""
        bridge._pending_joins["Bob"] = time.monotonic()

        bridge.frm_client.get_chat_messages.return_value = [
            ChatMessage(
                timestamp=1, server_timestamp=100.0,
                sender="Bob", message_type="System",
                message="<PlayerName/> has joined the game!",
            ),
        ]

        await bridge.poll_game_chat()

        bridge.signal_client.send_to_group.assert_called_once_with(
            "[Server] Bob joined the game"
        )
        assert "Bob" not in bridge._pending_joins

    @pytest.mark.asyncio
    async def test_system_join_leave_suppressed_no_pending(self, bridge):
        """System join/leave message with no matching pending event is suppressed."""
        bridge.frm_client.get_chat_messages.return_value = [
            ChatMessage(
                timestamp=1, server_timestamp=100.0,
                sender="Unknown", message_type="System",
                message="<PlayerName/> has joined the game!",
            ),
        ]

        await bridge.poll_game_chat()

        bridge.signal_client.send_to_group.assert_not_called()

    @pytest.mark.asyncio
    async def test_other_system_messages_forwarded(self, bridge):
        """Non-join/leave System messages are forwarded normally."""
        bridge.frm_client.get_chat_messages.return_value = [
            ChatMessage(
                timestamp=1, server_timestamp=100.0,
                sender="Server", message_type="System",
                message="Autosave complete",
            ),
        ]

        await bridge.poll_game_chat()

        bridge.signal_client.send_to_group.assert_called_once()
        call_arg = bridge.signal_client.send_to_group.call_args[0][0]
        assert "[System] Autosave complete" == call_arg

    @pytest.mark.asyncio
    async def test_player_messages_unaffected(self, bridge):
        """Regular player chat messages are not affected by the filter."""
        bridge.frm_client.get_chat_messages.return_value = [
            ChatMessage(
                timestamp=1, server_timestamp=100.0,
                sender="GamePlayer", message_type="Player",
                message="Hello everyone!",
            ),
        ]

        await bridge.poll_game_chat()

        bridge.signal_client.send_to_group.assert_called_once()
        call_arg = bridge.signal_client.send_to_group.call_args[0][0]
        assert "[GamePlayer] Hello everyone!" == call_arg

    @pytest.mark.asyncio
    async def test_mixed_messages_only_join_leave_handled(self, bridge):
        """In a batch, only System join/leave messages are handled specially."""
        bridge._pending_joins["NewPlayer"] = time.monotonic()

        bridge.frm_client.get_chat_messages.return_value = [
            ChatMessage(
                timestamp=1, server_timestamp=100.0,
                sender="NewPlayer", message_type="System",
                message="<PlayerName/> has joined the game!",
            ),
            ChatMessage(
                timestamp=2, server_timestamp=101.0,
                sender="SomePlayer", message_type="Player",
                message="Welcome!",
            ),
            ChatMessage(
                timestamp=3, server_timestamp=102.0,
                sender="Server", message_type="System",
                message="Autosave complete",
            ),
        ]

        await bridge.poll_game_chat()

        # 3 calls: confirmed join + player message + system save
        assert bridge.signal_client.send_to_group.call_count == 3
        calls = [c[0][0] for c in bridge.signal_client.send_to_group.call_args_list]
        assert "[Server] NewPlayer joined the game" in calls
        assert "[SomePlayer] Welcome!" in calls
        assert "[System] Autosave complete" in calls

    @pytest.mark.asyncio
    async def test_bot_messages_still_skipped(self, bridge):
        """Messages from the bot itself are still skipped."""
        bridge.frm_client.get_chat_messages.return_value = [
            ChatMessage(
                timestamp=1, server_timestamp=100.0,
                sender=bridge.config.bot_name, message_type="Player",
                message="Some bot message",
            ),
        ]

        await bridge.poll_game_chat()

        bridge.signal_client.send_to_group.assert_not_called()
