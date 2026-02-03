"""Signal API client wrapper with websocket support for json-rpc mode."""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import requests
import websockets

from text_processing import Attachment, parse_attachments

logger = logging.getLogger(__name__)


@dataclass
class SignalMessage:
    """Represents a received Signal message."""

    sender: str
    sender_uuid: Optional[str]
    text: str
    timestamp: int
    group_id: Optional[str] = None
    is_group: bool = False
    attachments: list[Attachment] = field(default_factory=list)
    has_sticker: bool = False


class SignalClient:
    """Wrapper for Signal CLI REST API interactions with websocket support."""

    def __init__(
        self,
        api_url: str,
        phone_number: str,
        group_id: Optional[str] = None,
    ):
        self.api_url = api_url.rstrip("/")
        self.phone_number = phone_number
        self.group_id = group_id  # Full format: group.xxx or internal format
        self._ws_url = self.api_url.replace("http://", "ws://").replace("https://", "wss://")
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

        # Extract internal group ID for matching incoming messages
        self._internal_group_id: Optional[str] = None
        if group_id:
            if group_id.startswith("group."):
                # Decode the base64 part after "group." to get internal ID
                import base64
                try:
                    encoded = group_id[6:]  # Remove "group." prefix
                    self._internal_group_id = base64.b64decode(encoded).decode("utf-8")
                except Exception:
                    self._internal_group_id = group_id
            else:
                self._internal_group_id = group_id

    def is_our_group(self, incoming_group_id: Optional[str]) -> bool:
        """Check if an incoming message's group ID matches our configured group."""
        if not incoming_group_id or not self._internal_group_id:
            return False
        return incoming_group_id == self._internal_group_id

    def send_message(self, text: str, group_id: Optional[str] = None, recipient: Optional[str] = None) -> bool:
        """Send a message to a group or individual recipient."""
        # Prioritize explicit recipient over group
        if recipient:
            recipients = [recipient]
        elif group_id:
            recipients = [group_id]
        elif self.group_id:
            recipients = [self.group_id]
        else:
            logger.warning("No recipient or group specified")
            return False

        payload: dict[str, Any] = {
            "message": text,
            "number": self.phone_number,
            "recipients": recipients,
        }

        try:
            response = self._session.post(
                f"{self.api_url}/v2/send",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            if "timestamp" in data:
                logger.debug("Sent message: %s", text[:50])
                return True
            elif "error" in data:
                logger.error("Failed to send: %s", data["error"])
                return False
            return True
        except Exception as e:
            logger.error("Failed to send Signal message: %s", e)
            return False

    def send_to_group(self, text: str) -> bool:
        """Send a message to the configured group."""
        if not self.group_id:
            logger.warning("No group configured")
            return False
        return self.send_message(text, group_id=self.group_id)

    def send_dm(self, text: str, recipient: str) -> bool:
        """Send a direct message to a specific recipient (UUID or username)."""
        return self.send_message(text, recipient=recipient)

    async def receive_messages_ws(self, timeout: float = 5.0) -> list[SignalMessage]:
        """Receive messages via websocket (for json-rpc mode)."""
        messages = []
        uri = f"{self._ws_url}/v1/receive/{self.phone_number}"

        try:
            async with websockets.connect(uri) as ws:
                while True:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                        msg = self._parse_message(json.loads(raw))
                        if msg:
                            messages.append(msg)
                        # Short timeout for subsequent messages
                        timeout = 0.5
                    except asyncio.TimeoutError:
                        break
        except Exception as e:
            logger.error("Websocket receive error: %s", e)

        return messages

    def _parse_message(self, raw: dict) -> Optional[SignalMessage]:
        """Parse a raw message envelope into a SignalMessage."""
        envelope = raw.get("envelope", {})
        data_message = envelope.get("dataMessage")

        if not data_message:
            return None

        text = data_message.get("message", "")

        # Parse attachments
        raw_attachments = data_message.get("attachments", [])
        attachments = parse_attachments(raw_attachments) if raw_attachments else []

        # Check for sticker
        has_sticker = "sticker" in data_message

        # Skip messages with no content (no text, no attachments, no sticker)
        if not text and not attachments and not has_sticker:
            return None

        # Skip messages from ourselves
        source_number = envelope.get("sourceNumber")
        if source_number == self.phone_number:
            return None

        sender = envelope.get("sourceName") or source_number or "Unknown"
        sender_uuid = envelope.get("sourceUuid")
        timestamp = data_message.get("timestamp", 0)

        group_info = data_message.get("groupInfo", {})
        group_id = group_info.get("groupId")
        is_group = group_id is not None

        return SignalMessage(
            sender=sender,
            sender_uuid=sender_uuid,
            text=text,
            timestamp=timestamp,
            group_id=group_id,
            is_group=is_group,
            attachments=attachments,
            has_sticker=has_sticker,
        )

    def send_read_receipt(self, recipient: str, timestamp: int) -> bool:
        """Send a read receipt for a message."""
        payload = {
            "receipt_type": "read",
            "recipient": recipient,
            "timestamp": timestamp,
        }

        try:
            response = self._session.post(
                f"{self.api_url}/v1/receipts/{self.phone_number}",
                json=payload,
                timeout=10,
            )
            if response.status_code == 204:
                logger.debug("Sent read receipt to %s", recipient)
                return True
            return False
        except Exception as e:
            logger.debug("Failed to send read receipt: %s", e)
            return False

    def health_check(self) -> bool:
        """Check if Signal API is reachable."""
        try:
            response = self._session.get(f"{self.api_url}/v1/about", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error("Signal API health check failed: %s", e)
            return False
