"""Tests for config module."""

import os
from unittest.mock import patch

from config import Config


class TestConfigDefaults:
    """Tests for Config default values."""

    def test_default_signal_api_url(self):
        """Test default Signal API URL."""
        config = Config()
        assert config.signal_api_url == "http://localhost:8080"

    def test_default_frm_api_url(self):
        """Test default FRM API URL."""
        config = Config()
        assert config.frm_api_url == "http://localhost:8082"

    def test_default_poll_interval(self):
        """Test default poll interval."""
        config = Config()
        assert config.poll_interval == 2.0

    def test_default_log_level(self):
        """Test default log level."""
        config = Config()
        assert config.log_level == "INFO"

    def test_default_bot_name(self):
        """Test default bot name."""
        config = Config()
        assert config.bot_name == "SignalBot"

    def test_default_server_port(self):
        """Test default server port."""
        config = Config()
        assert config.server_port == 7777

    def test_default_empty_strings(self):
        """Test default empty string values."""
        config = Config()
        assert config.signal_phone_number == ""
        assert config.frm_access_token == ""
        assert config.server_api_url == ""
        assert config.server_api_token == ""
        assert config.server_host == ""
        assert config.server_password == ""

    def test_default_none_values(self):
        """Test default None values."""
        config = Config()
        assert config.signal_group_id is None

    def test_default_empty_list(self):
        """Test default empty list values."""
        config = Config()
        assert config.signal_recipients == []


class TestConfigFromEnv:
    """Tests for Config.from_env() method."""

    def test_from_env_with_all_values(self):
        """Test loading all config values from environment."""
        env_vars = {
            "SIGNAL_API_URL": "http://signal:8080",
            "SIGNAL_PHONE_NUMBER": "+1234567890",
            "SIGNAL_GROUP_ID": "group.abc123",
            "SIGNAL_RECIPIENTS": "user1,user2,user3",
            "FRM_API_URL": "http://frm:8082",
            "FRM_ACCESS_TOKEN": "secret-token",
            "SERVER_API_URL": "https://server:7777",
            "SERVER_API_TOKEN": "server-token",
            "POLL_INTERVAL": "5.0",
            "LOG_LEVEL": "DEBUG",
            "BOT_NAME": "MyBot",
            "SERVER_HOST": "game.example.com",
            "SERVER_PORT": "15777",
            "SERVER_PASSWORD": "secret123",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

        assert config.signal_api_url == "http://signal:8080"
        assert config.signal_phone_number == "+1234567890"
        assert config.signal_group_id == "group.abc123"
        assert config.signal_recipients == ["user1", "user2", "user3"]
        assert config.frm_api_url == "http://frm:8082"
        assert config.frm_access_token == "secret-token"
        assert config.server_api_url == "https://server:7777"
        assert config.server_api_token == "server-token"
        assert config.poll_interval == 5.0
        assert config.log_level == "DEBUG"
        assert config.bot_name == "MyBot"
        assert config.server_host == "game.example.com"
        assert config.server_port == 15777
        assert config.server_password == "secret123"

    def test_from_env_with_defaults(self):
        """Test loading config with default values."""
        env_vars = {
            "SIGNAL_PHONE_NUMBER": "+1234567890",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

        assert config.signal_api_url == "http://localhost:8080"
        assert config.signal_phone_number == "+1234567890"
        assert config.frm_api_url == "http://localhost:8082"
        assert config.frm_timeout == 10.0
        assert config.poll_interval == 2.0
        assert config.log_level == "INFO"
        assert config.bot_name == "SignalBot"

    def test_from_env_frm_timeout(self):
        """Test FRM_TIMEOUT is loaded from environment."""
        env_vars = {"FRM_TIMEOUT": "15.0"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
        assert config.frm_timeout == 15.0
        assert isinstance(config.frm_timeout, float)

    def test_from_env_empty_group_id_is_none(self):
        """Test that empty SIGNAL_GROUP_ID results in None."""
        env_vars = {
            "SIGNAL_GROUP_ID": "",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

        assert config.signal_group_id is None

    def test_from_env_whitespace_group_id_is_none(self):
        """Test that whitespace-only SIGNAL_GROUP_ID results in None."""
        env_vars = {
            "SIGNAL_GROUP_ID": "   ",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

        assert config.signal_group_id is None

    def test_from_env_recipients_parsing(self):
        """Test SIGNAL_RECIPIENTS parsing with various formats."""
        # Test with spaces around commas
        env_vars = {"SIGNAL_RECIPIENTS": "user1 , user2 , user3"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
        assert config.signal_recipients == ["user1", "user2", "user3"]

        # Test with empty entries
        env_vars = {"SIGNAL_RECIPIENTS": "user1,,user2,"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
        assert config.signal_recipients == ["user1", "user2"]

        # Test with single recipient
        env_vars = {"SIGNAL_RECIPIENTS": "user1"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
        assert config.signal_recipients == ["user1"]

    def test_from_env_empty_recipients(self):
        """Test empty SIGNAL_RECIPIENTS results in empty list."""
        env_vars = {"SIGNAL_RECIPIENTS": ""}
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
        assert config.signal_recipients == []

    def test_from_env_poll_interval_conversion(self):
        """Test POLL_INTERVAL is converted to float."""
        env_vars = {"POLL_INTERVAL": "3"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
        assert config.poll_interval == 3.0
        assert isinstance(config.poll_interval, float)

    def test_from_env_server_port_conversion(self):
        """Test SERVER_PORT is converted to int."""
        env_vars = {"SERVER_PORT": "15000"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
        assert config.server_port == 15000
        assert isinstance(config.server_port, int)


class TestConfigValidation:
    """Tests for Config.validate() method."""

    def test_validate_missing_phone_number(self):
        """Test validation fails when phone number is missing."""
        config = Config()
        errors = config.validate()

        assert len(errors) == 1
        assert "SIGNAL_PHONE_NUMBER is required" in errors[0]

    def test_validate_valid_config_dm_only(self):
        """Test validation passes for DM-only configuration."""
        config = Config(signal_phone_number="+1234567890")
        errors = config.validate()

        assert errors == []

    def test_validate_group_without_frm_token(self):
        """Test validation fails when group is set but FRM token is missing."""
        config = Config(
            signal_phone_number="+1234567890",
            signal_group_id="group.abc123",
            frm_access_token="",  # Empty token
        )
        errors = config.validate()

        assert len(errors) == 1
        assert "FRM_ACCESS_TOKEN is required for group chat bridging" in errors[0]

    def test_validate_group_with_frm_token(self):
        """Test validation passes when group and FRM token are both set."""
        config = Config(
            signal_phone_number="+1234567890",
            signal_group_id="group.abc123",
            frm_access_token="secret-token",
        )
        errors = config.validate()

        assert errors == []

    def test_validate_multiple_errors(self):
        """Test validation returns multiple errors."""
        config = Config(
            signal_phone_number="",  # Missing
            signal_group_id="group.abc123",  # Set but no FRM token
        )
        errors = config.validate()

        assert len(errors) == 2
        assert any("SIGNAL_PHONE_NUMBER" in e for e in errors)
        assert any("FRM_ACCESS_TOKEN" in e for e in errors)


class TestConfigEdgeCases:
    """Tests for Config edge cases."""

    def test_config_with_custom_values(self):
        """Test Config with custom values."""
        config = Config(
            signal_api_url="http://custom:9000",
            signal_phone_number="+9876543210",
            signal_group_id="group.custom",
            signal_recipients=["a", "b", "c"],
            frm_api_url="http://custom-frm:9001",
            frm_access_token="custom-token",
            server_api_url="https://custom-server:9002",
            server_api_token="custom-server-token",
            poll_interval=10.5,
            log_level="WARNING",
            bot_name="CustomBot",
            server_host="custom.example.com",
            server_port=12345,
            server_password="custom-password",
        )

        assert config.signal_api_url == "http://custom:9000"
        assert config.poll_interval == 10.5
        assert config.server_port == 12345
        assert len(config.signal_recipients) == 3

    def test_config_is_dataclass(self):
        """Test Config is a proper dataclass with equality."""
        config1 = Config(signal_phone_number="+123")
        config2 = Config(signal_phone_number="+123")
        config3 = Config(signal_phone_number="+456")

        assert config1 == config2
        assert config1 != config3
