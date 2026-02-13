"""Tests for GrafanaClient."""

import pytest
from unittest.mock import MagicMock, patch

from config import GrafanaPanel
from grafana_client import GrafanaClient


@pytest.fixture
def sample_panels():
    """Return sample Grafana panels."""
    return [
        GrafanaPanel(name="power", dashboard_uid="abc123", panel_id=1),
        GrafanaPanel(name="production", dashboard_uid="abc123", panel_id=2),
        GrafanaPanel(name="electricity", dashboard_uid="def456", panel_id=5),
    ]


@pytest.fixture
def grafana_client(sample_panels):
    """Create a GrafanaClient with mocked session."""
    with patch("grafana_client.requests.Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        client = GrafanaClient(
            api_url="http://grafana:3000",
            api_key="test-api-key",
            panels=sample_panels,
            default_width=800,
            default_height=400,
            default_time_range="6h",
        )
        client._session = mock_session
        return client


class TestGrafanaClientInit:
    """Tests for GrafanaClient initialization."""

    def test_strips_trailing_slash(self, sample_panels):
        """Test URL trailing slash is stripped."""
        client = GrafanaClient(
            api_url="http://grafana:3000/",
            api_key="key",
            panels=sample_panels,
        )
        assert client.api_url == "http://grafana:3000"

    def test_panels_indexed_by_lowercase_name(self, grafana_client):
        """Test panels are stored by lowercase name."""
        assert "power" in grafana_client.panels
        assert "production" in grafana_client.panels
        assert "electricity" in grafana_client.panels


class TestGetPanelNames:
    """Tests for get_panel_names."""

    def test_returns_sorted_names(self, grafana_client):
        """Test panel names are returned sorted."""
        names = grafana_client.get_panel_names()
        assert names == ["electricity", "power", "production"]

    def test_empty_panels(self):
        """Test with no panels configured."""
        client = GrafanaClient(
            api_url="http://grafana:3000",
            api_key="key",
            panels=[],
        )
        assert client.get_panel_names() == []


class TestRenderPanel:
    """Tests for render_panel."""

    def test_render_success(self, grafana_client):
        """Test successful panel render."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"\x89PNG\r\n\x1a\nfakeimage"
        mock_response.headers = {"Content-Type": "image/png"}
        grafana_client._session.get.return_value = mock_response

        result = grafana_client.render_panel("power")

        assert result == b"\x89PNG\r\n\x1a\nfakeimage"
        call_args = grafana_client._session.get.call_args
        url = call_args[0][0]
        assert "/render/d-solo/abc123" in url
        assert "panelId=1" in url
        assert "width=800" in url
        assert "height=400" in url
        assert "from=now-6h" in url

    def test_render_with_custom_time_range(self, grafana_client):
        """Test render with custom time range."""
        mock_response = MagicMock()
        mock_response.content = b"image"
        mock_response.headers = {"Content-Type": "image/png"}
        grafana_client._session.get.return_value = mock_response

        grafana_client.render_panel("power", time_range="24h")

        url = grafana_client._session.get.call_args[0][0]
        assert "from=now-24h" in url

    def test_render_with_custom_dimensions(self, grafana_client):
        """Test render with custom width and height."""
        mock_response = MagicMock()
        mock_response.content = b"image"
        mock_response.headers = {"Content-Type": "image/png"}
        grafana_client._session.get.return_value = mock_response

        grafana_client.render_panel("power", width=1200, height=600)

        url = grafana_client._session.get.call_args[0][0]
        assert "width=1200" in url
        assert "height=600" in url

    def test_render_unknown_panel(self, grafana_client):
        """Test render with unknown panel name."""
        result = grafana_client.render_panel("nonexistent")
        assert result is None

    def test_render_case_insensitive(self, grafana_client):
        """Test panel name lookup is case insensitive."""
        mock_response = MagicMock()
        mock_response.content = b"image"
        mock_response.headers = {"Content-Type": "image/png"}
        grafana_client._session.get.return_value = mock_response

        result = grafana_client.render_panel("Power")
        assert result is not None

    def test_render_connection_error(self, grafana_client):
        """Test render when Grafana is unreachable."""
        import requests
        grafana_client._session.get.side_effect = requests.ConnectionError()

        result = grafana_client.render_panel("power")
        assert result is None

    def test_render_timeout(self, grafana_client):
        """Test render when Grafana times out."""
        import requests
        grafana_client._session.get.side_effect = requests.Timeout()

        result = grafana_client.render_panel("power")
        assert result is None

    def test_render_http_error(self, grafana_client):
        """Test render when Grafana returns an error status."""
        import requests
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        grafana_client._session.get.return_value = mock_response

        result = grafana_client.render_panel("power")
        assert result is None

    def test_render_non_image_response(self, grafana_client):
        """Test render when Grafana returns non-image content."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/html"}
        grafana_client._session.get.return_value = mock_response

        result = grafana_client.render_panel("power")
        assert result is None


class TestHealthCheck:
    """Tests for health_check."""

    def test_health_check_success(self, grafana_client):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        grafana_client._session.get.return_value = mock_response

        assert grafana_client.health_check() is True

    def test_health_check_failure(self, grafana_client):
        """Test failed health check."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        grafana_client._session.get.return_value = mock_response

        assert grafana_client.health_check() is False

    def test_health_check_connection_error(self, grafana_client):
        """Test health check when unreachable."""
        grafana_client._session.get.side_effect = Exception("Connection refused")

        assert grafana_client.health_check() is False
