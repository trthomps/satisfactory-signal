"""Tests for CommandHandler in main module."""

import pytest
from unittest.mock import MagicMock

from config import Config
from frm_client import FRMClient, Player, PowerStats
from server_api_client import ServerAPIClient, SessionInfo
from main import CommandHandler


@pytest.fixture
def mock_frm():
    """Create a mock FRM client."""
    frm = MagicMock(spec=FRMClient)
    frm.is_online = True
    frm.last_error = ""
    return frm


@pytest.fixture
def mock_server():
    """Create a mock Server API client."""
    return MagicMock(spec=ServerAPIClient)


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config(
        signal_phone_number="+1234567890",
        signal_group_id="group.test",
        frm_access_token="token",
        server_host="game.example.com",
        server_port=7777,
        server_password="secret",
    )


@pytest.fixture
def handler(mock_frm, config, mock_server):
    """Create a CommandHandler with mocks."""
    return CommandHandler(mock_frm, config, mock_server)


@pytest.fixture
def handler_no_server(mock_frm, config):
    """Create a CommandHandler without server client."""
    return CommandHandler(mock_frm, config, None)


class TestCommandHandlerBasics:
    """Tests for basic CommandHandler functionality."""

    def test_handle_with_slash_prefix(self, handler):
        """Test handling command with slash prefix."""
        result = handler.handle("/help")
        assert "Commands:" in result

    def test_handle_without_slash_prefix(self, handler):
        """Test handling command without slash prefix."""
        result = handler.handle("help")
        assert "Commands:" in result

    def test_handle_empty_string_shows_help(self, handler):
        """Test empty string shows help."""
        result = handler.handle("")
        assert "Commands:" in result

    def test_handle_unknown_command(self, handler):
        """Test unknown command returns error message."""
        result = handler.handle("unknowncommand")
        assert "Unknown command" in result

    def test_handle_server_offline(self, handler, mock_frm):
        """Test handling when server is offline."""
        mock_frm.is_online = False
        mock_frm.last_error = "Connection refused"
        mock_frm.get_players.return_value = []

        result = handler.handle("list")

        assert "Server Offline" in result
        assert "Connection refused" in result


class TestCmdHelp:
    """Tests for help command."""

    def test_help_lists_commands(self, handler):
        """Test help lists all available commands."""
        result = handler.cmd_help("")

        assert "Commands:" in result
        assert "list" in result
        assert "status" in result
        assert "power" in result
        assert "storage" in result
        assert "connect" in result


class TestCmdList:
    """Tests for list/players command."""

    def test_list_with_players(self, handler, mock_frm):
        """Test listing online players."""
        mock_frm.get_players.return_value = [
            Player(name="Player1", player_id="id1", ping=50),
            Player(name="Player2", player_id="id2", ping=100),
        ]

        result = handler.cmd_list("")

        assert "Online players (2)" in result
        assert "Player1" in result
        assert "Player2" in result
        assert "50ms" in result

    def test_list_no_players(self, handler, mock_frm):
        """Test listing when no players online."""
        mock_frm.get_players.return_value = []

        result = handler.cmd_list("")

        assert "No players online" in result

    def test_list_player_no_ping(self, handler, mock_frm):
        """Test listing player with zero ping."""
        mock_frm.get_players.return_value = [
            Player(name="Player1", player_id="id1", ping=0),
        ]

        result = handler.cmd_list("")

        assert "Player1" in result
        assert "ms" not in result  # No ping displayed


class TestCmdPower:
    """Tests for power command."""

    def test_power_normal(self, handler, mock_frm):
        """Test normal power status."""
        mock_frm.get_power.return_value = PowerStats(
            total_production=1500.0,
            total_consumption=1200.0,
            max_consumption=1800.0,
            battery_percent=75.0,
            battery_capacity=100.0,
            fuse_triggered=False,
        )

        result = handler.cmd_power("")

        assert "Status: OK" in result
        assert "1500.0 MW" in result
        assert "1200.0 MW" in result
        assert "+300.0 MW" in result  # Headroom
        assert "Battery: 75%" in result

    def test_power_tripped(self, handler, mock_frm):
        """Test power when fuse is tripped."""
        mock_frm.get_power.return_value = PowerStats(
            total_production=1000.0,
            total_consumption=1500.0,
            max_consumption=1800.0,
            battery_percent=0.0,
            battery_capacity=0.0,
            fuse_triggered=True,
        )

        result = handler.cmd_power("")

        assert "Status: TRIPPED" in result

    def test_power_no_battery(self, handler, mock_frm):
        """Test power without battery."""
        mock_frm.get_power.return_value = PowerStats(
            total_production=1000.0,
            total_consumption=800.0,
            max_consumption=1200.0,
            battery_percent=0.0,
            battery_capacity=0.0,
            fuse_triggered=False,
        )

        result = handler.cmd_power("")

        assert "Battery" not in result

    def test_power_unavailable(self, handler, mock_frm):
        """Test power when data unavailable."""
        mock_frm.get_power.return_value = None

        result = handler.cmd_power("")

        assert "unavailable" in result.lower()


class TestCmdStatus:
    """Tests for status command."""

    def test_status_online(self, handler, mock_frm):
        """Test status when server is online."""
        mock_frm.get_session_info.return_value = {
            "SessionName": "Test Session",
            "TotalPlayDurationText": "10h 30m",
            "PassedDays": 5,
            "IsDay": True,
        }
        mock_frm.get_players.return_value = [
            Player(name="P1", player_id="id1", ping=50),
        ]
        mock_frm.is_online = True

        result = handler.cmd_status("")

        assert "Test Session" in result
        assert "ONLINE" in result
        assert "Day 5" in result

    def test_status_offline(self, handler, mock_frm):
        """Test status when server is offline."""
        mock_frm.get_session_info.return_value = None
        mock_frm.is_online = False

        result = handler.cmd_status("")

        assert "OFFLINE" in result


class TestCmdSession:
    """Tests for session command."""

    def test_session_success(self, handler, mock_server):
        """Test session info retrieval."""
        mock_server.get_session_info.return_value = SessionInfo(
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

        result = handler.cmd_session("")

        assert "Test Session" in result
        assert "2/4" in result
        assert "Tech Tier: 5" in result
        assert "10h 0m" in result
        assert "30.0/30" in result

    def test_session_paused(self, handler, mock_server):
        """Test session info when paused."""
        mock_server.get_session_info.return_value = SessionInfo(
            session_name="Test",
            players_online=0,
            player_limit=4,
            tech_tier=1,
            game_phase="Phase 1",
            total_playtime_seconds=0,
            tick_rate=30.0,
            is_paused=True,
            active_schematic="None",
        )

        result = handler.cmd_session("")

        assert "PAUSED" in result

    def test_session_with_schematic(self, handler, mock_server):
        """Test session info with active research."""
        mock_server.get_session_info.return_value = SessionInfo(
            session_name="Test",
            players_online=1,
            player_limit=4,
            tech_tier=3,
            game_phase="Phase 2",
            total_playtime_seconds=3600,
            tick_rate=30.0,
            is_paused=False,
            active_schematic="Coal Power",
        )

        result = handler.cmd_session("")

        assert "Researching: Coal Power" in result

    def test_session_no_server_api(self, handler_no_server):
        """Test session without server API configured."""
        result = handler_no_server.cmd_session("")

        assert "not configured" in result.lower()

    def test_session_unavailable(self, handler, mock_server):
        """Test session when unavailable."""
        mock_server.get_session_info.return_value = None

        result = handler.cmd_session("")

        assert "unavailable" in result.lower()


class TestCmdSettings:
    """Tests for settings command."""

    def test_settings_success(self, handler, mock_server):
        """Test settings retrieval."""
        mock_server.get_server_options.return_value = {
            "auto_pause": True,
            "autosave_on_disconnect": True,
            "autosave_interval": 300,
            "seasonal_events": True,
            "network_quality": 3,
            "send_gameplay_data": False,
        }

        result = handler.cmd_settings("")

        assert "Auto-Pause: Yes" in result
        assert "Autosave Interval: 5 min" in result
        assert "Network Quality: Ultra" in result

    def test_settings_no_server_api(self, handler_no_server):
        """Test settings without server API."""
        result = handler_no_server.cmd_settings("")

        assert "not configured" in result.lower()


class TestCmdCheats:
    """Tests for cheats command."""

    def test_cheats_none_enabled(self, handler, mock_server):
        """Test when no cheats are enabled."""
        mock_server.get_advanced_settings.return_value = {
            "creative_mode": False,
            "god_mode": False,
            "flight_mode": False,
            "no_build_cost": False,
            "no_fuel_cost": False,
            "no_power": False,
            "no_unlock_cost": False,
            "all_tiers_unlocked": False,
            "all_schematics_unlocked": False,
            "all_alt_recipes": False,
            "no_arachnids": False,
        }

        result = handler.cmd_cheats("")

        assert "None enabled" in result

    def test_cheats_some_enabled(self, handler, mock_server):
        """Test when some cheats are enabled."""
        mock_server.get_advanced_settings.return_value = {
            "creative_mode": True,
            "god_mode": True,
            "flight_mode": False,
            "no_build_cost": False,
            "no_fuel_cost": False,
            "no_power": False,
            "no_unlock_cost": False,
            "all_tiers_unlocked": False,
            "all_schematics_unlocked": False,
            "all_alt_recipes": False,
            "no_arachnids": True,
        }

        result = handler.cmd_cheats("")

        assert "Cheats Enabled:" in result
        assert "Creative Mode" in result
        assert "God Mode" in result
        assert "No Spiders" in result


class TestCmdSaves:
    """Tests for saves command."""

    def test_saves_success(self, handler, mock_server):
        """Test saves retrieval."""
        mock_server.get_saves.return_value = [
            {
                "name": "Save1",
                "session": "Session1",
                "is_current_session": True,
                "playtime_seconds": 7200,
                "save_time": "2026.02.03-10.30.00",
                "is_modded": False,
            },
            {
                "name": "Save2",
                "session": "Session1",
                "is_current_session": True,
                "playtime_seconds": 3600,
                "save_time": "2026.02.02-15.00.00",
                "is_modded": True,
            },
        ]

        result = handler.cmd_saves("")

        assert "Save1" in result
        assert "2h0m" in result
        assert "[modded]" in result
        assert "* = current session" in result

    def test_saves_empty(self, handler, mock_server):
        """Test when no saves found."""
        mock_server.get_saves.return_value = []

        result = handler.cmd_saves("")

        assert "No saves found" in result


class TestCmdFactory:
    """Tests for factory command."""

    def test_factory_success(self, handler, mock_frm):
        """Test factory stats retrieval."""
        mock_frm.get_factory_stats.return_value = {
            "total_buildings": 100,
            "running": 80,
            "idle": 20,
            "avg_efficiency": 85.5,
        }

        result = handler.cmd_factory("")

        assert "Buildings: 100" in result
        assert "Running: 80" in result
        assert "Idle: 20" in result
        assert "85.5%" in result

    def test_factory_unavailable(self, handler, mock_frm):
        """Test factory when unavailable."""
        mock_frm.get_factory_stats.return_value = None

        result = handler.cmd_factory("")

        assert "unavailable" in result.lower()


class TestCmdTrains:
    """Tests for trains command."""

    def test_trains_success(self, handler, mock_frm):
        """Test trains retrieval."""
        mock_frm.get_trains.return_value = [
            {"name": "Train1", "speed": 100, "status": "Running", "power": 50},
            {"name": "Train2", "speed": 0, "status": "Stopped", "power": 0},
        ]

        result = handler.cmd_trains("")

        assert "Trains (2)" in result
        assert "Train1" in result
        assert "100 km/h" in result
        assert "stopped" in result

    def test_trains_empty(self, handler, mock_frm):
        """Test when no trains."""
        mock_frm.get_trains.return_value = []

        result = handler.cmd_trains("")

        assert "No trains found" in result


class TestCmdDrones:
    """Tests for drones command."""

    def test_drones_success(self, handler, mock_frm):
        """Test drones retrieval."""
        mock_frm.get_drones.return_value = [
            {"home": "Station A", "destination": "Station B", "status": "Flying", "speed": 50},
        ]

        result = handler.cmd_drones("")

        assert "Drones (1)" in result
        assert "Station A -> Station B" in result

    def test_drones_empty(self, handler, mock_frm):
        """Test when no drones."""
        mock_frm.get_drones.return_value = []

        result = handler.cmd_drones("")

        assert "No drones found" in result


class TestCmdVehicles:
    """Tests for vehicles command."""

    def test_vehicles_success(self, handler, mock_frm):
        """Test vehicles retrieval."""
        mock_frm.get_vehicles.return_value = [
            {"type": "Truck", "name": "Truck1", "speed": 50, "gear": 3, "autopilot": True, "fuel_pct": 80},
            {"type": "Tractor", "name": "Tractor1", "speed": 0, "gear": 0, "autopilot": False, "fuel_pct": 50},
        ]

        result = handler.cmd_vehicles("")

        assert "Vehicles (2)" in result
        assert "Truck" in result
        assert "autopilot" in result
        assert "parked" in result

    def test_vehicles_empty(self, handler, mock_frm):
        """Test when no vehicles."""
        mock_frm.get_vehicles.return_value = []

        result = handler.cmd_vehicles("")

        assert "No vehicles found" in result


class TestCmdGenerators:
    """Tests for generators command."""

    def test_generators_success(self, handler, mock_frm):
        """Test generators retrieval."""
        mock_frm.get_generators.return_value = {
            "Coal Generator": {"count": 10, "capacity": 750, "producing": 600},
            "Fuel Generator": {"count": 5, "capacity": 750, "producing": 750},
        }

        result = handler.cmd_generators("")

        assert "Power Generation" in result
        assert "Coal Generator" in result
        assert "10x" in result
        assert "Total:" in result

    def test_generators_empty(self, handler, mock_frm):
        """Test when no generators."""
        mock_frm.get_generators.return_value = {}

        result = handler.cmd_generators("")

        assert "No generators found" in result


class TestCmdStorage:
    """Tests for storage command."""

    def test_storage_success(self, handler, mock_frm):
        """Test storage search."""
        mock_frm.get_storage_items.return_value = [
            {"name": "Iron Ore", "amount": 10000},
            {"name": "Iron Ingot", "amount": 5000},
        ]

        result = handler.cmd_storage("iron")

        assert "Iron Ore" in result
        assert "10,000" in result
        assert "matching: iron" in result

    def test_storage_no_search(self, handler, mock_frm):
        """Test storage without search term."""
        mock_frm.get_storage_items.return_value = [
            {"name": "Item1", "amount": 100},
        ]

        result = handler.cmd_storage("")

        assert "Storage" in result
        assert "1 items" in result
        assert "matching:" not in result

    def test_storage_empty_with_search(self, handler, mock_frm):
        """Test storage with no matches."""
        mock_frm.get_storage_items.return_value = []

        result = handler.cmd_storage("nonexistent")

        assert "No items matching" in result

    def test_storage_empty_no_search(self, handler, mock_frm):
        """Test storage with nothing in storage."""
        mock_frm.get_storage_items.return_value = []

        result = handler.cmd_storage("")

        assert "No items in storage" in result


class TestCmdProd:
    """Tests for prod command."""

    def test_prod_success(self, handler, mock_frm):
        """Test production stats."""
        mock_frm.get_production_stats.return_value = [
            {"name": "Iron Ingot", "prod": 100, "cons": 50, "net": 50},
            {"name": "Copper Ingot", "prod": 50, "cons": 60, "net": -10},
        ]

        result = handler.cmd_prod("")

        assert "Production" in result
        assert "Iron Ingot" in result
        assert "+50.0" in result
        assert "-10.0" in result

    def test_prod_empty(self, handler, mock_frm):
        """Test when no production data."""
        mock_frm.get_production_stats.return_value = []

        result = handler.cmd_prod("")

        assert "No production data" in result


class TestCmdSink:
    """Tests for sink command."""

    def test_sink_success(self, handler, mock_frm):
        """Test AWESOME Sink stats."""
        mock_frm.get_sink_stats.return_value = {
            "coupons": 10,
            "total_points": 100000,
            "points_to_coupon": 5000,
            "percent": 50.0,
        }

        result = handler.cmd_sink("")

        assert "AWESOME Sink" in result
        assert "Coupons: 10" in result
        assert "100,000" in result
        assert "50.0%" in result

    def test_sink_unavailable(self, handler, mock_frm):
        """Test when sink data unavailable."""
        mock_frm.get_sink_stats.return_value = None

        result = handler.cmd_sink("")

        assert "unavailable" in result.lower()


class TestCmdSwitches:
    """Tests for switches command."""

    def test_switches_success(self, handler, mock_frm):
        """Test power switches."""
        mock_frm.get_switches.return_value = [
            {"name": "Main Power", "is_on": True},
            {"name": "Backup", "is_on": False},
        ]

        result = handler.cmd_switches("")

        assert "Power Switches (2)" in result
        assert "Main Power: ON" in result
        assert "Backup: OFF" in result

    def test_switches_empty(self, handler, mock_frm):
        """Test when no switches."""
        mock_frm.get_switches.return_value = []

        result = handler.cmd_switches("")

        assert "No power switches found" in result


class TestCmdConnect:
    """Tests for connect command."""

    def test_connect_configured(self, handler):
        """Test connect with configured server info."""
        result = handler.cmd_connect("")

        assert "Server Connection Info" in result
        assert "game.example.com" in result
        assert "7777" in result
        assert "secret" in result

    def test_connect_not_configured(self, config, mock_frm):
        """Test connect without configured server info."""
        config.server_host = ""
        handler = CommandHandler(mock_frm, config, None)

        result = handler.cmd_connect("")

        assert "not configured" in result.lower()
