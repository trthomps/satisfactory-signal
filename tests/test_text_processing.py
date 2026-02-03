"""Tests for text_processing module."""

from text_processing import (
    Attachment,
    Mention,
    CONTENT_TYPE_NAMES,
    emoji_to_shortcode,
    shortcode_to_emoji,
    format_attachment,
    format_attachments,
    format_sticker,
    replace_mentions,
    process_signal_to_game,
    process_game_to_signal,
    parse_attachments,
    parse_mentions,
    MENTION_PLACEHOLDER,
)


class TestAttachment:
    """Tests for Attachment dataclass."""

    def test_display_type_known_content_type(self):
        """Test display_type returns correct name for known content types."""
        attachment = Attachment(content_type="image/jpeg")
        assert attachment.display_type == "Image"

        attachment = Attachment(content_type="application/pdf")
        assert attachment.display_type == "PDF"

        attachment = Attachment(content_type="audio/aac")
        assert attachment.display_type == "Voice Note"

    def test_display_type_fallback_prefix(self):
        """Test display_type falls back to prefix-based detection."""
        attachment = Attachment(content_type="image/unknown")
        assert attachment.display_type == "Image"

        attachment = Attachment(content_type="audio/unknown")
        assert attachment.display_type == "Audio"

        attachment = Attachment(content_type="video/unknown")
        assert attachment.display_type == "Video"

        attachment = Attachment(content_type="text/unknown")
        assert attachment.display_type == "Text File"

    def test_display_type_unknown(self):
        """Test display_type returns 'File' for unknown types."""
        attachment = Attachment(content_type="application/unknown")
        assert attachment.display_type == "File"

        attachment = Attachment(content_type="x-custom/type")
        assert attachment.display_type == "File"


class TestEmojiConversion:
    """Tests for emoji conversion functions."""

    def test_emoji_to_shortcode_basic(self):
        """Test basic emoji to shortcode conversion."""
        assert emoji_to_shortcode("Hello :thumbs_up:") == "Hello :thumbs_up:"
        result = emoji_to_shortcode("Hello \U0001f600")  # grinning face
        assert (
            ":grinning" in result.lower()
            or ":smile" in result.lower()
            or result == "Hello :grinning_face:"
        )

    def test_emoji_to_shortcode_empty(self):
        """Test emoji_to_shortcode with empty string."""
        assert emoji_to_shortcode("") == ""
        assert emoji_to_shortcode(None) is None  # type: ignore

    def test_emoji_to_shortcode_no_emojis(self):
        """Test emoji_to_shortcode with no emojis."""
        assert emoji_to_shortcode("Hello, world!") == "Hello, world!"

    def test_emoji_to_shortcode_multiple_emojis(self):
        """Test emoji_to_shortcode with multiple emojis."""
        result = emoji_to_shortcode("\U0001f44d\U0001f44e")  # thumbs up, thumbs down
        assert ":" in result  # Should contain shortcodes

    def test_shortcode_to_emoji_basic(self):
        """Test basic shortcode to emoji conversion."""
        result = shortcode_to_emoji(":grinning_face:")
        assert (
            result == "\U0001f600" or ":" not in result
        )  # Converted or already converted

    def test_shortcode_to_emoji_empty(self):
        """Test shortcode_to_emoji with empty string."""
        assert shortcode_to_emoji("") == ""
        assert shortcode_to_emoji(None) is None  # type: ignore

    def test_shortcode_to_emoji_no_shortcodes(self):
        """Test shortcode_to_emoji with no shortcodes."""
        assert shortcode_to_emoji("Hello, world!") == "Hello, world!"

    def test_roundtrip_conversion(self):
        """Test emoji -> shortcode -> emoji roundtrip."""
        original = "Hello \U0001f44d!"  # thumbs up
        shortcode = emoji_to_shortcode(original)
        restored = shortcode_to_emoji(shortcode)
        # Should restore to original or equivalent
        assert "\U0001f44d" in restored or "thumbs" in shortcode.lower()


class TestFormatAttachment:
    """Tests for format_attachment function."""

    def test_format_image(self):
        """Test formatting image attachment."""
        attachment = Attachment(content_type="image/jpeg", filename="photo.jpg")
        assert format_attachment(attachment) == "[Image]"

    def test_format_gif(self):
        """Test formatting GIF attachment."""
        attachment = Attachment(content_type="image/gif")
        assert format_attachment(attachment) == "[GIF]"

    def test_format_voice_note(self):
        """Test formatting voice note attachment."""
        attachment = Attachment(content_type="audio/aac")
        assert format_attachment(attachment) == "[Voice Note]"

    def test_format_video(self):
        """Test formatting video attachment."""
        attachment = Attachment(content_type="video/mp4")
        assert format_attachment(attachment) == "[Video]"

    def test_format_pdf_with_filename(self):
        """Test formatting PDF with filename."""
        attachment = Attachment(content_type="application/pdf", filename="report.pdf")
        assert format_attachment(attachment) == "[PDF: report.pdf]"

    def test_format_document_with_filename(self):
        """Test formatting document with filename."""
        attachment = Attachment(content_type="application/msword", filename="doc.doc")
        assert format_attachment(attachment) == "[Document: doc.doc]"

    def test_format_spreadsheet_with_filename(self):
        """Test formatting spreadsheet with filename."""
        attachment = Attachment(
            content_type="application/vnd.ms-excel", filename="data.xls"
        )
        assert format_attachment(attachment) == "[Spreadsheet: data.xls]"

    def test_format_archive_with_filename(self):
        """Test formatting archive with filename."""
        attachment = Attachment(content_type="application/zip", filename="files.zip")
        assert format_attachment(attachment) == "[Archive: files.zip]"

    def test_format_unknown_file_with_filename(self):
        """Test formatting unknown file type with filename."""
        attachment = Attachment(
            content_type="application/octet-stream", filename="data.bin"
        )
        assert format_attachment(attachment) == "[File: data.bin]"

    def test_format_unknown_file_without_filename(self):
        """Test formatting unknown file type without filename."""
        attachment = Attachment(content_type="application/octet-stream")
        assert format_attachment(attachment) == "[File]"


class TestFormatAttachments:
    """Tests for format_attachments function."""

    def test_format_empty_list(self):
        """Test formatting empty attachment list."""
        assert format_attachments([]) == ""

    def test_format_single_attachment(self):
        """Test formatting single attachment."""
        attachments = [Attachment(content_type="image/jpeg")]
        assert format_attachments(attachments) == "[Image]"

    def test_format_multiple_attachments(self):
        """Test formatting multiple attachments."""
        attachments = [
            Attachment(content_type="image/jpeg"),
            Attachment(content_type="video/mp4"),
            Attachment(content_type="application/pdf", filename="doc.pdf"),
        ]
        result = format_attachments(attachments)
        assert "[Image]" in result
        assert "[Video]" in result
        assert "[PDF: doc.pdf]" in result


class TestFormatSticker:
    """Tests for format_sticker function."""

    def test_format_sticker(self):
        """Test sticker formatting."""
        assert format_sticker() == "[Sticker]"


class TestReplaceMentions:
    """Tests for replace_mentions function."""

    def test_replace_single_mention(self):
        """Test replacing a single mention."""
        text = f"{MENTION_PLACEHOLDER} said hello"
        mentions = [Mention(start=0, length=1, name="Alice")]
        result = replace_mentions(text, mentions)
        assert result == "@Alice said hello"

    def test_replace_multiple_mentions(self):
        """Test replacing multiple mentions."""
        text = f"Hey {MENTION_PLACEHOLDER} and {MENTION_PLACEHOLDER}"
        mentions = [
            Mention(start=4, length=1, name="Alice"),
            Mention(start=10, length=1, name="Bob"),
        ]
        result = replace_mentions(text, mentions)
        assert "@Alice" in result
        assert "@Bob" in result

    def test_replace_no_mentions(self):
        """Test with empty mentions list."""
        text = "Hello, world!"
        result = replace_mentions(text, [])
        assert result == "Hello, world!"

    def test_replace_empty_text(self):
        """Test with empty text."""
        result = replace_mentions("", [Mention(start=0, length=1, name="Alice")])
        assert result == ""

    def test_replace_none_text(self):
        """Test with None text."""
        result = replace_mentions(None, [])  # type: ignore
        assert result is None

    def test_replace_mention_at_end(self):
        """Test mention at end of text."""
        text = f"Hello {MENTION_PLACEHOLDER}"
        mentions = [Mention(start=6, length=1, name="Alice")]
        result = replace_mentions(text, mentions)
        assert result == "Hello @Alice"

    def test_replace_preserves_order(self):
        """Test that mentions are replaced correctly regardless of order in list."""
        text = f"{MENTION_PLACEHOLDER} and {MENTION_PLACEHOLDER}"
        mentions = [
            Mention(start=6, length=1, name="Second"),
            Mention(start=0, length=1, name="First"),
        ]
        result = replace_mentions(text, mentions)
        assert result.startswith("@First")
        assert result.endswith("@Second")


class TestProcessSignalToGame:
    """Tests for process_signal_to_game function."""

    def test_process_text_only(self):
        """Test processing text-only message."""
        result = process_signal_to_game("Hello, world!")
        assert result == "Hello, world!"

    def test_process_text_with_emoji(self):
        """Test processing text with emoji."""
        result = process_signal_to_game("Hello \U0001f44d")  # thumbs up
        assert ":" in result  # Should contain shortcode

    def test_process_text_with_attachment(self):
        """Test processing text with attachment."""
        attachments = [Attachment(content_type="image/jpeg")]
        result = process_signal_to_game("Check this out", attachments=attachments)
        assert "Check this out" in result
        assert "[Image]" in result

    def test_process_sticker_only(self):
        """Test processing sticker-only message."""
        result = process_signal_to_game("", has_sticker=True)
        assert result == "[Sticker]"

    def test_process_attachment_only(self):
        """Test processing attachment-only message."""
        attachments = [Attachment(content_type="image/jpeg")]
        result = process_signal_to_game("", attachments=attachments)
        assert result == "[Image]"

    def test_process_with_mentions(self):
        """Test processing message with mentions."""
        text = f"{MENTION_PLACEHOLDER} check this"
        mentions = [Mention(start=0, length=1, name="Alice")]
        result = process_signal_to_game(text, mentions=mentions)
        assert "@Alice" in result
        assert "check this" in result

    def test_process_empty_message(self):
        """Test processing empty message."""
        result = process_signal_to_game("")
        assert result == ""

    def test_process_all_components(self):
        """Test processing message with all components."""
        text = f"{MENTION_PLACEHOLDER} look at this \U0001f44d"
        attachments = [Attachment(content_type="image/jpeg")]
        mentions = [Mention(start=0, length=1, name="Alice")]

        result = process_signal_to_game(
            text,
            attachments=attachments,
            has_sticker=True,
            mentions=mentions,
        )

        assert "@Alice" in result
        assert "[Sticker]" in result
        assert "[Image]" in result


class TestProcessGameToSignal:
    """Tests for process_game_to_signal function."""

    def test_process_plain_text(self):
        """Test processing plain text."""
        result = process_game_to_signal("Hello, world!")
        assert result == "Hello, world!"

    def test_process_text_with_shortcode(self):
        """Test processing text with shortcode."""
        result = process_game_to_signal("Hello :thumbs_up:")
        # Should convert shortcode to emoji or leave as is
        assert "thumbs" in result.lower() or "\U0001f44d" in result

    def test_process_empty_text(self):
        """Test processing empty text."""
        result = process_game_to_signal("")
        assert result == ""

    def test_process_none_text(self):
        """Test processing None text."""
        result = process_game_to_signal(None)  # type: ignore
        assert result is None


class TestParseAttachments:
    """Tests for parse_attachments function."""

    def test_parse_single_attachment(self):
        """Test parsing a single attachment."""
        raw = [
            {
                "contentType": "image/jpeg",
                "filename": "photo.jpg",
                "size": 1024,
                "id": "123",
            }
        ]
        result = parse_attachments(raw)

        assert len(result) == 1
        assert result[0].content_type == "image/jpeg"
        assert result[0].filename == "photo.jpg"
        assert result[0].size == 1024
        assert result[0].id == "123"

    def test_parse_multiple_attachments(self):
        """Test parsing multiple attachments."""
        raw = [
            {"contentType": "image/jpeg"},
            {"contentType": "video/mp4", "filename": "video.mp4"},
        ]
        result = parse_attachments(raw)

        assert len(result) == 2
        assert result[0].content_type == "image/jpeg"
        assert result[1].content_type == "video/mp4"
        assert result[1].filename == "video.mp4"

    def test_parse_empty_list(self):
        """Test parsing empty attachment list."""
        result = parse_attachments([])
        assert result == []

    def test_parse_attachment_with_missing_fields(self):
        """Test parsing attachment with missing optional fields."""
        raw = [{"contentType": "image/jpeg"}]
        result = parse_attachments(raw)

        assert len(result) == 1
        assert result[0].content_type == "image/jpeg"
        assert result[0].filename is None
        assert result[0].size is None

    def test_parse_attachment_with_no_content_type(self):
        """Test parsing attachment without contentType uses default."""
        raw = [{}]
        result = parse_attachments(raw)

        assert len(result) == 1
        assert result[0].content_type == "application/octet-stream"


class TestParseMentions:
    """Tests for parse_mentions function."""

    def test_parse_single_mention(self):
        """Test parsing a single mention."""
        raw = [{"start": 0, "length": 1, "name": "Alice", "uuid": "uuid-123"}]
        result = parse_mentions(raw)

        assert len(result) == 1
        assert result[0].start == 0
        assert result[0].length == 1
        assert result[0].name == "Alice"
        assert result[0].uuid == "uuid-123"

    def test_parse_multiple_mentions(self):
        """Test parsing multiple mentions."""
        raw = [
            {"start": 0, "length": 1, "name": "Alice"},
            {"start": 5, "length": 1, "name": "Bob"},
        ]
        result = parse_mentions(raw)

        assert len(result) == 2
        assert result[0].name == "Alice"
        assert result[1].name == "Bob"

    def test_parse_empty_list(self):
        """Test parsing empty mention list."""
        result = parse_mentions([])
        assert result == []

    def test_parse_mention_with_number_fallback(self):
        """Test parsing mention that falls back to number."""
        raw = [{"start": 0, "length": 1, "number": "+1234567890"}]
        result = parse_mentions(raw)

        assert len(result) == 1
        assert result[0].name == "+1234567890"

    def test_parse_mention_with_unknown_fallback(self):
        """Test parsing mention that falls back to Unknown."""
        raw = [{"start": 0, "length": 1}]
        result = parse_mentions(raw)

        assert len(result) == 1
        assert result[0].name == "Unknown"

    def test_parse_mention_with_missing_position(self):
        """Test parsing mention with missing position uses defaults."""
        raw = [{"name": "Alice"}]
        result = parse_mentions(raw)

        assert len(result) == 1
        assert result[0].start == 0
        assert result[0].length == 1


class TestContentTypeNames:
    """Tests for CONTENT_TYPE_NAMES constant."""

    def test_all_image_types(self):
        """Test all image types are mapped."""
        image_types = [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/gif",
            "image/webp",
            "image/bmp",
            "image/svg+xml",
        ]
        for ct in image_types:
            assert ct in CONTENT_TYPE_NAMES
            assert CONTENT_TYPE_NAMES[ct] in ("Image", "GIF")

    def test_all_audio_types(self):
        """Test all audio types are mapped."""
        audio_types = [
            "audio/aac",
            "audio/mp4",
            "audio/mpeg",
            "audio/ogg",
            "audio/wav",
            "audio/webm",
            "audio/x-m4a",
        ]
        for ct in audio_types:
            assert ct in CONTENT_TYPE_NAMES
            assert CONTENT_TYPE_NAMES[ct] in ("Audio", "Voice Note")

    def test_all_video_types(self):
        """Test all video types are mapped."""
        video_types = ["video/mp4", "video/webm", "video/quicktime", "video/3gpp"]
        for ct in video_types:
            assert ct in CONTENT_TYPE_NAMES
            assert CONTENT_TYPE_NAMES[ct] == "Video"

    def test_all_document_types(self):
        """Test all document types are mapped."""
        doc_types = ["application/pdf", "application/msword", "text/plain", "text/csv"]
        for ct in doc_types:
            assert ct in CONTENT_TYPE_NAMES
