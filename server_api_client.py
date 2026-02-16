"""Satisfactory Dedicated Server API client."""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """Server session information."""

    session_name: str
    players_online: int
    player_limit: int
    tech_tier: int
    game_phase: str
    total_playtime_seconds: int
    tick_rate: float
    is_paused: bool
    active_schematic: str


class ServerAPIClient:
    """Client for Satisfactory Dedicated Server API."""

    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token
        self._client = httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_token}",
            },
            # Disable SSL verification for self-signed certs
            verify=False,
            timeout=httpx.Timeout(10),
        )

    async def _call(self, function: str, data: Optional[dict] = None) -> Optional[dict]:
        """Make an API call to the server."""
        payload: dict = {"function": function}
        if data:
            payload["data"] = data

        try:
            response = await self._client.post(
                f"{self.api_url}/api/v1",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("data")
        except httpx.HTTPStatusError as e:
            logger.error("Server API request failed (%s): %s", function, e)
            return None

    async def get_session_info(self) -> Optional[SessionInfo]:
        """Get current session information."""
        data = await self._call("QueryServerState")
        if not data:
            return None

        state = data.get("serverGameState", {})

        # Parse game phase to human readable
        phase_raw = state.get("gamePhase", "")
        phase = self._parse_game_phase(phase_raw)

        # Parse active schematic
        schematic = state.get("activeSchematic", "None")
        if schematic == "None" or not schematic:
            schematic = "None"

        return SessionInfo(
            session_name=state.get("activeSessionName", "Unknown"),
            players_online=state.get("numConnectedPlayers", 0),
            player_limit=state.get("playerLimit", 0),
            tech_tier=state.get("techTier", 0),
            game_phase=phase,
            total_playtime_seconds=state.get("totalGameDuration", 0),
            tick_rate=state.get("averageTickRate", 0.0),
            is_paused=state.get("isGamePaused", False),
            active_schematic=schematic,
        )

    def _parse_game_phase(self, phase_raw: str) -> str:
        """Convert game phase path to human readable string."""
        # Example: /Script/FactoryGame.FGGamePhase'/Game/FactoryGame/GamePhases/GP_Project_Assembly_Phase_1.GP_Project_Assembly_Phase_1'
        if "Phase_1" in phase_raw:
            return "Phase 1 (0/1 deliveries)"
        elif "Phase_2" in phase_raw:
            return "Phase 2 (1/2 deliveries)"
        elif "Phase_3" in phase_raw:
            return "Phase 3 (2/3 deliveries)"
        elif "Phase_4" in phase_raw:
            return "Phase 4 (3/4 deliveries)"
        elif "Phase_5" in phase_raw:
            return "Phase 5 (4/5 deliveries)"
        elif "Victory" in phase_raw or "Phase_6" in phase_raw:
            return "Complete!"
        return "Unknown"

    async def get_server_options(self) -> Optional[dict]:
        """Get server options/settings."""
        data = await self._call("GetServerOptions")
        if not data:
            return None

        options = data.get("serverOptions", {})

        # Parse the FG.* keys into readable format
        return {
            "auto_pause": options.get("FG.DSAutoPause", "False") == "True",
            "autosave_on_disconnect": options.get("FG.DSAutoSaveOnDisconnect", "False") == "True",
            "autosave_interval": int(float(options.get("FG.AutosaveInterval", "300"))),
            "seasonal_events": options.get("FG.DisableSeasonalEvents", "True") != "True",
            "network_quality": int(options.get("FG.NetworkQuality", "3")),
            "send_gameplay_data": options.get("FG.SendGameplayData", "False") == "True",
        }

    async def get_advanced_settings(self) -> Optional[dict]:
        """Get advanced game settings (cheats)."""
        data = await self._call("GetAdvancedGameSettings")
        if not data:
            return None

        settings = data.get("advancedGameSettings", {})
        creative = data.get("creativeModeEnabled", False)

        # Parse settings into readable format
        return {
            "creative_mode": creative,
            "no_arachnids": settings.get("FG.GameRules.DisableArachnidCreatures", "False") == "True",
            "flight_mode": settings.get("FG.PlayerRules.FlightMode", "False") == "True",
            "god_mode": settings.get("FG.PlayerRules.GodMode", "False") == "True",
            "no_build_cost": settings.get("FG.PlayerRules.NoBuildCost", "False") == "True",
            "no_fuel_cost": settings.get("FG.GameRules.NoFuelCost", "False") == "True",
            "no_power": settings.get("FG.GameRules.NoPower", "False") == "True",
            "no_unlock_cost": settings.get("FG.GameRules.NoUnlockCost", "False") == "True",
            "all_tiers_unlocked": settings.get("FG.GameRules.GiveAllTiers", "False") == "True",
            "all_schematics_unlocked": settings.get("FG.GameRules.UnlockAllResearchSchematics", "False") == "True",
            "all_alt_recipes": settings.get("FG.GameRules.UnlockInstantAltRecipes", "False") == "True",
        }

    async def get_saves(self, limit: int = 5) -> list[dict]:
        """Get recent save files."""
        data = await self._call("EnumerateSessions")
        if not data:
            return []

        saves = []
        sessions = data.get("sessions", [])

        # Get current session index to identify active session
        current_idx = data.get("currentSessionIndex", 0)

        for i, session in enumerate(sessions):
            session_name = session.get("sessionName", "Unknown")
            is_current = i == current_idx

            for header in session.get("saveHeaders", [])[:limit]:
                saves.append({
                    "name": header.get("saveName", "Unknown"),
                    "session": session_name,
                    "is_current_session": is_current,
                    "playtime_seconds": header.get("playDurationSeconds", 0),
                    "save_time": header.get("saveDateTime", ""),
                    "is_modded": header.get("isModdedSave", False),
                })

            if len(saves) >= limit:
                break

        return saves[:limit]

    async def health_check(self) -> bool:
        """Check if server API is reachable."""
        try:
            response = await self._client.post(
                f"{self.api_url}/api/v1",
                json={"function": "HealthCheck", "data": {"ClientCustomData": ""}},
                timeout=httpx.Timeout(5),
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("health") == "healthy"
            return False
        except Exception as e:
            logger.error("Server API health check failed: %s", e)
            return False
