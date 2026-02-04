"""FRM (Ficsit Remote Monitoring) API client wrapper."""

import logging
from dataclasses import dataclass
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """Represents a Satisfactory chat message."""

    timestamp: int
    server_timestamp: float
    sender: str
    message_type: str  # "Player", "System", or "Ada"
    message: str


@dataclass
class Player:
    """Represents a player in the game."""

    name: str
    player_id: str
    ping: int
    dead: bool = False
    health: float = 100.0


@dataclass
class PowerStats:
    """Represents power grid statistics."""

    total_production: float
    total_consumption: float
    max_consumption: float
    battery_percent: float
    battery_capacity: float
    fuse_triggered: bool


class FRMClient:
    """Wrapper for FRM API interactions."""

    def __init__(self, api_url: str, access_token: str):
        self.api_url = api_url.rstrip("/")
        self.access_token = access_token
        self.last_timestamp: float = 0.0
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        self._is_online: bool = False
        self._last_error: str = ""

    @property
    def is_online(self) -> bool:
        """Check if the FRM server was reachable on the last request."""
        return self._is_online

    def _set_online(self, online: bool, error: str = "") -> None:
        """Update online status and log state changes."""
        if online and not self._is_online:
            logger.info("Game server is now ONLINE")
        elif not online and self._is_online:
            logger.warning("Game server is now OFFLINE: %s", error or "Connection lost")

        self._is_online = online
        self._last_error = error

    @property
    def last_error(self) -> str:
        """Get the last error message."""
        return self._last_error

    def _get(self, endpoint: str) -> Optional[Any]:
        """Make a GET request to the FRM API."""
        try:
            response = self._session.get(
                f"{self.api_url}/{endpoint}",
                timeout=5,
            )
            response.raise_for_status()
            self._set_online(True)
            return response.json()
        except requests.ConnectionError:
            self._set_online(False, "Cannot connect to game server")
            return None
        except requests.Timeout:
            self._set_online(False, "Game server timeout")
            return None
        except requests.RequestException as e:
            self._set_online(False, f"Server error: {e}")
            logger.error("FRM API request failed (%s): %s", endpoint, e)
            return None

    def get_chat_messages(self) -> list[ChatMessage]:
        """Fetch chat messages from the game, returning only new ones."""
        messages: list[ChatMessage] = []
        data = self._get("getChatMessages")

        if not data:
            return messages

        try:
            for msg in data:
                server_ts = msg.get("ServerTimeStamp", 0.0)

                if server_ts <= self.last_timestamp:
                    continue

                messages.append(
                    ChatMessage(
                        timestamp=msg.get("TimeStamp", 0),
                        server_timestamp=server_ts,
                        sender=msg.get("Sender", "Unknown"),
                        message_type=msg.get("Type", "Player"),
                        message=msg.get("Message", ""),
                    )
                )

            if messages:
                self.last_timestamp = max(m.server_timestamp for m in messages)
                logger.debug(
                    "Received %d new chat messages, last timestamp: %f",
                    len(messages),
                    self.last_timestamp,
                )
        except (KeyError, ValueError) as e:
            logger.error("Failed to parse chat messages: %s", e)

        return messages

    def send_chat_message(
        self,
        message: str,
        sender: Optional[str] = None,
        color: Optional[dict[str, float]] = None,
    ) -> bool:
        """Send a chat message to the game."""
        payload: dict = {"message": message}

        if sender:
            payload["sender"] = sender[:32]

        if color:
            payload["color"] = color

        try:
            response = self._session.post(
                f"{self.api_url}/sendChatMessage",
                json=payload,
                headers={"X-FRM-Authorization": self.access_token},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if data and isinstance(data, list) and data[0].get("IsSent"):
                logger.debug("Sent chat message: %s", message[:50])
                return True
            else:
                logger.warning("Message not confirmed as sent: %s", data)
                return False

        except requests.RequestException as e:
            logger.error("Failed to send chat message: %s", e)
            return False

    def get_players(self) -> list[Player]:
        """Get list of online players."""
        players: list[Player] = []
        data = self._get("getPlayer")

        if not data:
            return players

        try:
            for p in data:
                # Only include online players with non-empty names
                if not p.get("Online", False):
                    continue
                name = p.get("Name", "").strip()
                if not name:
                    continue
                players.append(
                    Player(
                        name=name,
                        player_id=p.get("Id", ""),
                        ping=p.get("PingMs", 0),
                        dead=p.get("Dead", False),
                        health=p.get("PlayerHP", 100.0),
                    )
                )
        except (KeyError, ValueError) as e:
            logger.error("Failed to parse players: %s", e)

        return players

    def get_power(self) -> Optional[PowerStats]:
        """Get power grid statistics."""
        data = self._get("getPower")

        if not data:
            return None

        try:
            # FRM returns an array of power circuits, aggregate them
            total_prod = 0.0
            total_cons = 0.0
            max_cons = 0.0
            battery_pct = 0.0
            battery_cap = 0.0
            fuse_triggered = False

            for circuit in data:
                total_prod += circuit.get("PowerProduction", 0.0)
                total_cons += circuit.get("PowerConsumed", 0.0)
                max_cons += circuit.get("PowerMaxConsumed", 0.0)
                battery_pct = max(battery_pct, circuit.get("BatteryPercent", 0.0))
                battery_cap += circuit.get("BatteryCapacity", 0.0)
                if circuit.get("FuseTriggered", False):
                    fuse_triggered = True

            return PowerStats(
                total_production=total_prod,
                total_consumption=total_cons,
                max_consumption=max_cons,
                battery_percent=battery_pct,
                battery_capacity=battery_cap,
                fuse_triggered=fuse_triggered,
            )
        except (KeyError, ValueError) as e:
            logger.error("Failed to parse power stats: %s", e)
            return None

    def get_session_info(self) -> Optional[dict]:
        """Get session/server information."""
        return self._get("getSessionInfo")

    def get_factory_stats(self) -> Optional[dict]:
        """Get overall factory statistics."""
        data = self._get("getFactory")
        if not data:
            return None

        # Aggregate factory buildings by efficiency
        total_buildings = len(data)
        running = sum(1 for b in data if b.get("IsProducing", False))
        avg_efficiency = 0.0
        if data:
            # Productivity is already a percentage (0-100+)
            efficiencies = [b.get("Productivity", 0.0) for b in data]
            avg_efficiency = sum(efficiencies) / len(efficiencies)

        return {
            "total_buildings": total_buildings,
            "running": running,
            "idle": total_buildings - running,
            "avg_efficiency": avg_efficiency,
        }

    def get_trains(self) -> list[dict]:
        """Get train information."""
        data = self._get("getTrains")
        if not data:
            return []

        trains = []
        for t in data:
            trains.append({
                "name": t.get("Name", "Train"),
                "speed": t.get("ForwardSpeed", 0),
                "status": t.get("Status", "Unknown"),
                "power": t.get("PowerConsumed", 0),
            })
        return trains

    def get_drones(self) -> list[dict]:
        """Get drone information."""
        data = self._get("getDrone")
        if not data:
            return []

        drones = []
        for d in data:
            drones.append({
                "home": d.get("HomeStation", "Unknown"),
                "destination": d.get("PairedStation", "Unknown"),
                "status": d.get("CurrentFlyingMode", "Unknown"),
                "speed": d.get("FlyingSpeed", 0),
            })
        return drones

    def get_vehicles(self) -> list[dict]:
        """Get all vehicle information (trucks, tractors, explorers)."""
        vehicles = []

        for endpoint, vtype in [("getTruck", "Truck"), ("getTractor", "Tractor"), ("getExplorer", "Explorer")]:
            data = self._get(endpoint)
            if data:
                for v in data:
                    vehicles.append({
                        "type": vtype,
                        "name": v.get("Name", vtype),
                        "speed": v.get("ForwardSpeed", 0),
                        "gear": v.get("CurrentGear", 0),
                        "autopilot": v.get("AutoPilot", False),
                        "fuel_pct": v.get("FuelInventory", {}).get("PercentFull", 0) if isinstance(v.get("FuelInventory"), dict) else 0,
                    })
        return vehicles

    def get_generators(self) -> dict:
        """Get power generator statistics grouped by type."""
        data = self._get("getGenerators")
        if not data:
            return {}

        generators: dict[str, dict] = {}
        for g in data:
            name = g.get("Name", "Unknown")
            if name not in generators:
                generators[name] = {"count": 0, "capacity": 0, "producing": 0}

            generators[name]["count"] += 1
            generators[name]["capacity"] += g.get("ProductionCapacity", 0)
            if g.get("IsFullSpeed", False) or g.get("FuelAmount", 0) > 0:
                generators[name]["producing"] += g.get("ProductionCapacity", 0)

        return generators

    def get_storage_items(self, search: str = "") -> list[dict]:
        """Search for items in storage containers."""
        data = self._get("getStorageInv")
        if not data:
            return []

        items: dict[str, int] = {}
        search_lower = search.lower()

        for container in data:
            inventory = container.get("Inventory", [])
            for item in inventory:
                name = item.get("Name", "Unknown")
                amount = item.get("Amount", 0)

                if search_lower and search_lower not in name.lower():
                    continue

                if name in items:
                    items[name] += amount
                else:
                    items[name] = amount

        # Convert to sorted list
        return sorted(
            [{"name": k, "amount": v} for k, v in items.items()],
            key=lambda x: x["amount"],
            reverse=True,
        )

    def get_production_stats(self) -> list[dict]:
        """Get production/consumption rates."""
        data = self._get("getProdStats")
        if not data:
            return []

        # Filter to items with actual production or consumption
        stats = []
        for item in data:
            prod = item.get("CurrentProd", 0)
            cons = item.get("CurrentConsumed", 0)
            if prod > 0 or cons > 0:
                stats.append({
                    "name": item.get("Name", "Unknown"),
                    "prod": prod,
                    "cons": cons,
                    "net": prod - cons,
                })

        # Sort by net production
        return sorted(stats, key=lambda x: x["net"], reverse=True)

    def get_sink_stats(self) -> Optional[dict]:
        """Get AWESOME Sink statistics."""
        data = self._get("getResourceSink")
        if not data:
            return None

        # Usually just one entry
        sink = data[0] if data else {}
        return {
            "coupons": sink.get("NumCoupon", 0),
            "total_points": sink.get("TotalPoints", 0),
            "points_to_coupon": sink.get("PointsToCoupon", 0),
            "percent": sink.get("Percent", 0) * 100,
        }

    def get_switches(self) -> list[dict]:
        """Get power switch states."""
        data = self._get("getSwitches")
        if not data:
            return []

        switches = []
        for s in data:
            switches.append({
                "name": s.get("Name", "Switch"),
                "is_on": s.get("IsOn", False),
            })
        return switches

    def health_check(self) -> bool:
        """Check if FRM API is reachable."""
        try:
            response = self._session.get(
                f"{self.api_url}/getChatMessages",
                timeout=5,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error("FRM API health check failed: %s", e)
            return False

    def initialize_timestamp(self) -> None:
        """Initialize last_timestamp to current latest message to avoid replaying old messages."""
        data = self._get("getChatMessages")
        if data:
            self.last_timestamp = max(msg.get("ServerTimeStamp", 0.0) for msg in data)
            logger.info("Initialized FRM timestamp to %f", self.last_timestamp)
