"""Grafana API client for rendering dashboard panel images."""

import logging
from typing import Optional

import requests

from config import GrafanaPanel

logger = logging.getLogger(__name__)


class GrafanaClient:
    """Wrapper for Grafana render API interactions."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        panels: list[GrafanaPanel],
        default_width: int = 800,
        default_height: int = 400,
        default_time_range: str = "6h",
    ):
        self.api_url = api_url.rstrip("/")
        self.panels = {p.name.lower(): p for p in panels}
        self.default_width = default_width
        self.default_height = default_height
        self.default_time_range = default_time_range
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
        })

    def get_panel_names(self) -> list[str]:
        """Return sorted list of available panel names."""
        return sorted(self.panels.keys())

    def render_panel(
        self,
        panel_name: str,
        time_range: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Optional[bytes]:
        """Render a panel as a PNG image.

        Args:
            panel_name: Name of the panel (as configured in GRAFANA_PANELS).
            time_range: Time range string (e.g. "1h", "6h", "24h", "7d").
            width: Image width in pixels.
            height: Image height in pixels.

        Returns:
            PNG image bytes, or None on failure.
        """
        panel = self.panels.get(panel_name.lower())
        if not panel:
            return None

        tr = time_range or self.default_time_range
        w = width or self.default_width
        h = height or self.default_height

        url = (
            f"{self.api_url}/render/d-solo/{panel.dashboard_uid}"
            f"?orgId=1"
            f"&panelId={panel.panel_id}"
            f"&width={w}"
            f"&height={h}"
            f"&from=now-{tr}"
            f"&to=now"
        )

        try:
            response = self._session.get(url, timeout=30)
            response.raise_for_status()

            if "image/png" not in response.headers.get("Content-Type", ""):
                logger.error(
                    "Grafana returned non-image response: %s",
                    response.headers.get("Content-Type"),
                )
                return None

            logger.debug("Rendered panel '%s' (%d bytes)", panel_name, len(response.content))
            return response.content

        except requests.ConnectionError:
            logger.error("Cannot connect to Grafana at %s", self.api_url)
            return None
        except requests.Timeout:
            logger.error("Grafana render timed out for panel '%s'", panel_name)
            return None
        except requests.RequestException as e:
            logger.error("Grafana render failed for panel '%s': %s", panel_name, e)
            return None

    def health_check(self) -> bool:
        """Check if Grafana API is reachable."""
        try:
            response = self._session.get(f"{self.api_url}/api/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error("Grafana health check failed: %s", e)
            return False
