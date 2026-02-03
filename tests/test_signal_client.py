"""Tests for signal_client module."""

import base64
import pytest
from unittest.mock import MagicMock, patch

from signal_client import SignalClient, SignalMessage


class TestSignalClientInit:
    """Tests for SignalClient initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )

        assert client.api_url == "http://localhost:8080"
        assert client.phone_number == "+1234567890"
        assert client.group_id is None
        assert client._internal_group_id is None

    def test_init_with_trailing_slash(self):
        """Test that trailing slash is stripped from URL."""
        client = SignalClient(
            api_url="http://localhost:8080/",
            phone_number="+1234567890",
        )

        assert client.api_url == "http://localhost:8080"

    def test_init_ws_url_conversion(self):
        """Test websocket URL is correctly derived."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )
        assert client._ws_url == "ws://localhost:8080"

        client = SignalClient(
            api_url="https://secure.example.com:8080",
            phone_number="+1234567890",
        )
        assert client._ws_url == "wss://secure.example.com:8080"

    def test_init_with_group_id_prefixed(self):
        """Test initialization with group. prefixed group ID."""
        # Base64 encode "testgroupid" -> dGVzdGdyb3VwaWQ=
        group_id = "group.dGVzdGdyb3VwaWQ="
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
            group_id=group_id,
        )

        assert client.group_id == group_id
        assert client._internal_group_id == "testgroupid"

    def test_init_with_group_id_raw(self):
        """Test initialization with raw group ID (no prefix)."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
            group_id="rawgroupid",
        )

        assert client.group_id == "rawgroupid"
        assert client._internal_group_id == "rawgroupid"

    def test_init_with_invalid_base64_group(self):
        """Test initialization with invalid base64 in group ID."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
            group_id="group.invalid!!!base64",
        )

        # Should fall back to the original group_id
        assert client.group_id == "group.invalid!!!base64"


class TestSignalClientIsOurGroup:
    """Tests for SignalClient.is_our_group() method."""

    def test_is_our_group_matching(self):
        """Test matching group ID."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
            group_id="group.dGVzdGdyb3VwaWQ=",
        )

        assert client.is_our_group("testgroupid") is True

    def test_is_our_group_not_matching(self):
        """Test non-matching group ID."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
            group_id="group.dGVzdGdyb3VwaWQ=",
        )

        assert client.is_our_group("othergroupid") is False

    def test_is_our_group_none_incoming(self):
        """Test with None incoming group ID."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
            group_id="group.dGVzdGdyb3VwaWQ=",
        )

        assert client.is_our_group(None) is False

    def test_is_our_group_no_configured_group(self):
        """Test when no group is configured."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )

        assert client.is_our_group("anygroupid") is False


class TestSignalClientSendMessage:
    """Tests for SignalClient.send_message() method."""

    def test_send_message_to_group(self):
        """Test sending message to group."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
            group_id="group.abc123",
        )
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = {"timestamp": 123456}
        mock_response.raise_for_status = MagicMock()
        client._session.post.return_value = mock_response

        result = client.send_message("Hello!")

        assert result is True
        client._session.post.assert_called_once()
        call_args = client._session.post.call_args
        assert call_args[1]["json"]["message"] == "Hello!"
        assert "group.abc123" in call_args[1]["json"]["recipients"]

    def test_send_message_to_recipient(self):
        """Test sending message to specific recipient."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = {"timestamp": 123456}
        mock_response.raise_for_status = MagicMock()
        client._session.post.return_value = mock_response

        result = client.send_message("Hello!", recipient="+0987654321")

        assert result is True
        call_args = client._session.post.call_args
        assert "+0987654321" in call_args[1]["json"]["recipients"]

    def test_send_message_no_recipient_no_group(self):
        """Test sending message without recipient or group fails."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )
        client._session = MagicMock()

        result = client.send_message("Hello!")

        assert result is False
        client._session.post.assert_not_called()

    def test_send_message_with_error_response(self):
        """Test handling error response from API."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
            group_id="group.abc123",
        )
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Rate limited"}
        mock_response.raise_for_status = MagicMock()
        client._session.post.return_value = mock_response

        result = client.send_message("Hello!")

        assert result is False

    def test_send_message_exception(self):
        """Test handling exception during send."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
            group_id="group.abc123",
        )
        client._session = MagicMock()

        client._session.post.side_effect = Exception("Connection failed")

        result = client.send_message("Hello!")

        assert result is False


class TestSignalClientSendToGroup:
    """Tests for SignalClient.send_to_group() method."""

    def test_send_to_group_success(self):
        """Test successful group message."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
            group_id="group.abc123",
        )
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = {"timestamp": 123456}
        mock_response.raise_for_status = MagicMock()
        client._session.post.return_value = mock_response

        result = client.send_to_group("Hello group!")

        assert result is True

    def test_send_to_group_no_group_configured(self):
        """Test send_to_group without configured group."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )

        result = client.send_to_group("Hello!")

        assert result is False


class TestSignalClientSendDM:
    """Tests for SignalClient.send_dm() method."""

    def test_send_dm_success(self):
        """Test successful direct message."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = {"timestamp": 123456}
        mock_response.raise_for_status = MagicMock()
        client._session.post.return_value = mock_response

        result = client.send_dm("Hello!", "+0987654321")

        assert result is True
        call_args = client._session.post.call_args
        assert "+0987654321" in call_args[1]["json"]["recipients"]


class TestSignalClientParseMessage:
    """Tests for SignalClient._parse_message() method."""

    def test_parse_simple_message(self):
        """Test parsing a simple text message."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )

        raw = {
            "envelope": {
                "sourceNumber": "+0987654321",
                "sourceName": "TestUser",
                "sourceUuid": "uuid-123",
                "dataMessage": {
                    "message": "Hello, world!",
                    "timestamp": 1234567890000,
                },
            }
        }

        msg = client._parse_message(raw)

        assert msg is not None
        assert msg.sender == "TestUser"
        assert msg.sender_uuid == "uuid-123"
        assert msg.text == "Hello, world!"
        assert msg.timestamp == 1234567890000
        assert msg.is_group is False

    def test_parse_group_message(self):
        """Test parsing a group message."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
            group_id="group.dGVzdGdyb3VwaWQ=",
        )

        raw = {
            "envelope": {
                "sourceNumber": "+0987654321",
                "sourceName": "TestUser",
                "sourceUuid": "uuid-123",
                "dataMessage": {
                    "message": "Hello group!",
                    "timestamp": 1234567890000,
                    "groupInfo": {
                        "groupId": "testgroupid",
                    },
                },
            }
        }

        msg = client._parse_message(raw)

        assert msg is not None
        assert msg.is_group is True
        assert msg.group_id == "testgroupid"

    def test_parse_message_with_attachments(self):
        """Test parsing message with attachments."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )

        raw = {
            "envelope": {
                "sourceNumber": "+0987654321",
                "sourceName": "TestUser",
                "dataMessage": {
                    "message": "Check this out",
                    "timestamp": 1234567890000,
                    "attachments": [
                        {"contentType": "image/jpeg", "filename": "photo.jpg"},
                    ],
                },
            }
        }

        msg = client._parse_message(raw)

        assert msg is not None
        assert len(msg.attachments) == 1
        assert msg.attachments[0].content_type == "image/jpeg"

    def test_parse_message_with_mentions(self):
        """Test parsing message with mentions."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )

        raw = {
            "envelope": {
                "sourceNumber": "+0987654321",
                "sourceName": "TestUser",
                "dataMessage": {
                    "message": "\ufffc check this",
                    "timestamp": 1234567890000,
                    "mentions": [
                        {"start": 0, "length": 1, "name": "Alice"},
                    ],
                },
            }
        }

        msg = client._parse_message(raw)

        assert msg is not None
        assert len(msg.mentions) == 1
        assert msg.mentions[0].name == "Alice"

    def test_parse_message_with_sticker(self):
        """Test parsing message with sticker."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )

        raw = {
            "envelope": {
                "sourceNumber": "+0987654321",
                "sourceName": "TestUser",
                "dataMessage": {
                    "message": "",
                    "timestamp": 1234567890000,
                    "sticker": {"packId": "abc", "stickerId": 1},
                },
            }
        }

        msg = client._parse_message(raw)

        assert msg is not None
        assert msg.has_sticker is True

    def test_parse_message_no_data_message(self):
        """Test parsing envelope without dataMessage returns None."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )

        raw = {
            "envelope": {
                "sourceNumber": "+0987654321",
            }
        }

        msg = client._parse_message(raw)

        assert msg is None

    def test_parse_message_empty_content(self):
        """Test parsing message with no content returns None."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )

        raw = {
            "envelope": {
                "sourceNumber": "+0987654321",
                "dataMessage": {
                    "message": "",
                    "timestamp": 1234567890000,
                },
            }
        }

        msg = client._parse_message(raw)

        assert msg is None

    def test_parse_message_from_self(self):
        """Test parsing message from self returns None."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )

        raw = {
            "envelope": {
                "sourceNumber": "+1234567890",  # Same as client
                "dataMessage": {
                    "message": "Hello",
                    "timestamp": 1234567890000,
                },
            }
        }

        msg = client._parse_message(raw)

        assert msg is None

    def test_parse_message_sender_fallback(self):
        """Test sender falls back to source number if no name."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )

        raw = {
            "envelope": {
                "sourceNumber": "+0987654321",
                "dataMessage": {
                    "message": "Hello",
                    "timestamp": 1234567890000,
                },
            }
        }

        msg = client._parse_message(raw)

        assert msg is not None
        assert msg.sender == "+0987654321"


class TestSignalClientSendReadReceipt:
    """Tests for SignalClient.send_read_receipt() method."""

    def test_send_read_receipt_success(self):
        """Test successful read receipt."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 204
        client._session.post.return_value = mock_response

        result = client.send_read_receipt("+0987654321", 1234567890000)

        assert result is True

    def test_send_read_receipt_failure(self):
        """Test failed read receipt."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 400
        client._session.post.return_value = mock_response

        result = client.send_read_receipt("+0987654321", 1234567890000)

        assert result is False

    def test_send_read_receipt_exception(self):
        """Test read receipt with exception."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )
        client._session = MagicMock()

        client._session.post.side_effect = Exception("Connection failed")

        result = client.send_read_receipt("+0987654321", 1234567890000)

        assert result is False


class TestSignalClientHealthCheck:
    """Tests for SignalClient.health_check() method."""

    def test_health_check_success(self):
        """Test successful health check."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        client._session.get.return_value = mock_response

        result = client.health_check()

        assert result is True
        client._session.get.assert_called_with(
            "http://localhost:8080/v1/about",
            timeout=5,
        )

    def test_health_check_failure(self):
        """Test failed health check."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )
        client._session = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 500
        client._session.get.return_value = mock_response

        result = client.health_check()

        assert result is False

    def test_health_check_exception(self):
        """Test health check with exception."""
        client = SignalClient(
            api_url="http://localhost:8080",
            phone_number="+1234567890",
        )
        client._session = MagicMock()

        client._session.get.side_effect = Exception("Connection refused")

        result = client.health_check()

        assert result is False


class TestSignalMessage:
    """Tests for SignalMessage dataclass."""

    def test_signal_message_defaults(self):
        """Test SignalMessage default values."""
        msg = SignalMessage(
            sender="TestUser",
            sender_uuid="uuid-123",
            text="Hello",
            timestamp=1234567890000,
        )

        assert msg.group_id is None
        assert msg.is_group is False
        assert msg.attachments == []
        assert msg.has_sticker is False
        assert msg.mentions == []

    def test_signal_message_equality(self):
        """Test SignalMessage equality."""
        msg1 = SignalMessage(
            sender="User",
            sender_uuid="uuid",
            text="Hello",
            timestamp=123,
        )
        msg2 = SignalMessage(
            sender="User",
            sender_uuid="uuid",
            text="Hello",
            timestamp=123,
        )

        assert msg1 == msg2
