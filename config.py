"""Configuration management for the Satisfactory-Signal bridge."""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Bot configuration loaded from environment variables."""

    # Signal API settings
    signal_api_url: str = "http://localhost:8080"
    signal_phone_number: str = ""
    signal_group_id: Optional[str] = None
    signal_recipients: list[str] = field(default_factory=list)

    # FRM API settings
    frm_api_url: str = "http://localhost:8082"
    frm_access_token: str = ""

    # Dedicated Server API settings
    server_api_url: str = ""
    server_api_token: str = ""

    # Bot settings
    poll_interval: float = 2.0
    log_level: str = "INFO"
    bot_name: str = "SignalBot"

    # Server connection info (for /connect command)
    server_host: str = ""
    server_port: int = 7777
    server_password: str = ""

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        load_dotenv()

        recipients_str = os.getenv("SIGNAL_RECIPIENTS", "")
        recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]

        group_id = os.getenv("SIGNAL_GROUP_ID", "").strip() or None

        return cls(
            signal_api_url=os.getenv("SIGNAL_API_URL", "http://localhost:8080"),
            signal_phone_number=os.getenv("SIGNAL_PHONE_NUMBER", ""),
            signal_group_id=group_id,
            signal_recipients=recipients,
            frm_api_url=os.getenv("FRM_API_URL", "http://localhost:8082"),
            frm_access_token=os.getenv("FRM_ACCESS_TOKEN", ""),
            server_api_url=os.getenv("SERVER_API_URL", ""),
            server_api_token=os.getenv("SERVER_API_TOKEN", ""),
            poll_interval=float(os.getenv("POLL_INTERVAL", "2.0")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            bot_name=os.getenv("BOT_NAME", "SignalBot"),
            server_host=os.getenv("SERVER_HOST", ""),
            server_port=int(os.getenv("SERVER_PORT", "7777")),
            server_password=os.getenv("SERVER_PASSWORD", ""),
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not self.signal_phone_number:
            errors.append("SIGNAL_PHONE_NUMBER is required")

        # Group ID is optional - without it, only DM commands work
        # FRM token is only required if group bridging is enabled
        if self.signal_group_id and not self.frm_access_token:
            errors.append("FRM_ACCESS_TOKEN is required for group chat bridging")

        return errors
