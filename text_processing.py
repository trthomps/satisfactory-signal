"""Text processing utilities for emoji conversion and attachment handling."""

from dataclasses import dataclass
from typing import Optional

import emoji


# Content type to display name mapping
CONTENT_TYPE_NAMES: dict[str, str] = {
    # Images
    "image/jpeg": "Image",
    "image/jpg": "Image",
    "image/png": "Image",
    "image/gif": "GIF",
    "image/webp": "Image",
    "image/bmp": "Image",
    "image/svg+xml": "Image",
    # Audio
    "audio/aac": "Voice Note",
    "audio/mp4": "Voice Note",
    "audio/mpeg": "Audio",
    "audio/ogg": "Voice Note",
    "audio/wav": "Audio",
    "audio/webm": "Voice Note",
    "audio/x-m4a": "Audio",
    # Video
    "video/mp4": "Video",
    "video/webm": "Video",
    "video/quicktime": "Video",
    "video/3gpp": "Video",
    # Documents
    "application/pdf": "PDF",
    "application/msword": "Document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Document",
    "application/vnd.ms-excel": "Spreadsheet",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Spreadsheet",
    "application/vnd.ms-powerpoint": "Presentation",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "Presentation",
    "application/zip": "Archive",
    "application/x-rar-compressed": "Archive",
    "application/x-7z-compressed": "Archive",
    "application/gzip": "Archive",
    "text/plain": "Text File",
    "text/csv": "CSV",
    "application/json": "JSON",
    "application/xml": "XML",
}


@dataclass
class Attachment:
    """Represents a Signal message attachment."""

    content_type: str
    filename: Optional[str] = None
    size: Optional[int] = None
    id: Optional[str] = None

    @property
    def display_type(self) -> str:
        """Get human-readable attachment type."""
        # Check content type mapping
        if self.content_type in CONTENT_TYPE_NAMES:
            return CONTENT_TYPE_NAMES[self.content_type]

        # Fallback to generic categories based on mime type prefix
        if self.content_type.startswith("image/"):
            return "Image"
        elif self.content_type.startswith("audio/"):
            return "Audio"
        elif self.content_type.startswith("video/"):
            return "Video"
        elif self.content_type.startswith("text/"):
            return "Text File"

        # Default
        return "File"


def emoji_to_shortcode(text: str) -> str:
    """Convert Unicode emojis to :shortcode: format.

    Args:
        text: Text potentially containing emojis

    Returns:
        Text with emojis converted to shortcodes
    """
    if not text:
        return text

    return emoji.demojize(text)


def shortcode_to_emoji(text: str) -> str:
    """Convert :shortcode: format back to Unicode emojis.

    Args:
        text: Text potentially containing shortcodes

    Returns:
        Text with shortcodes converted to emojis
    """
    if not text:
        return text

    return emoji.emojize(text)


def format_attachment(attachment: Attachment) -> str:
    """Format a single attachment for display.

    Args:
        attachment: The attachment to format

    Returns:
        Formatted attachment string like [Image] or [File: document.pdf]
    """
    display_type = attachment.display_type

    # For generic files, include filename if available
    if display_type == "File" and attachment.filename:
        return f"[File: {attachment.filename}]"

    # For known types, just show the type
    # But include filename for documents if it's informative
    if display_type in ("PDF", "Document", "Spreadsheet", "Presentation", "Archive", "Text File", "CSV", "JSON", "XML"):
        if attachment.filename:
            return f"[{display_type}: {attachment.filename}]"

    return f"[{display_type}]"


def format_attachments(attachments: list[Attachment]) -> str:
    """Format multiple attachments for display.

    Args:
        attachments: List of attachments to format

    Returns:
        Formatted string representing all attachments
    """
    if not attachments:
        return ""

    return " ".join(format_attachment(a) for a in attachments)


def format_sticker() -> str:
    """Format a sticker for display.

    Returns:
        Formatted sticker string
    """
    return "[Sticker]"


def process_signal_to_game(text: str, attachments: Optional[list[Attachment]] = None, has_sticker: bool = False) -> str:
    """Process a Signal message for sending to the game.

    Converts emojis to shortcodes and appends attachment indicators.

    Args:
        text: The message text (may be empty)
        attachments: List of attachments (may be None or empty)
        has_sticker: Whether a sticker was included

    Returns:
        Processed text suitable for game chat
    """
    parts = []

    # Convert emojis in text
    if text:
        parts.append(emoji_to_shortcode(text))

    # Add sticker indicator
    if has_sticker:
        parts.append(format_sticker())

    # Add attachment indicators
    if attachments:
        parts.append(format_attachments(attachments))

    return " ".join(parts) if parts else ""


def process_game_to_signal(text: str) -> str:
    """Process a game message for sending to Signal.

    Converts shortcodes back to emojis.

    Args:
        text: The message text from the game

    Returns:
        Processed text with emojis restored
    """
    if not text:
        return text

    return shortcode_to_emoji(text)


def parse_attachments(raw_attachments: list[dict]) -> list[Attachment]:
    """Parse raw attachment data from Signal API.

    Args:
        raw_attachments: List of attachment dictionaries from Signal API

    Returns:
        List of Attachment objects
    """
    attachments = []
    for raw in raw_attachments:
        attachments.append(Attachment(
            content_type=raw.get("contentType", "application/octet-stream"),
            filename=raw.get("filename"),
            size=raw.get("size"),
            id=raw.get("id"),
        ))
    return attachments
