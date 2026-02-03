#!/usr/bin/env python3
"""Main entry point for the Satisfactory-Signal bridge bot."""

import asyncio
import logging
import signal
import sys
from typing import Optional

from config import Config
from frm_client import FRMClient
from server_api_client import ServerAPIClient
from signal_client import SignalClient, SignalMessage
from text_processing import process_game_to_signal, process_signal_to_game

# Global shutdown flag
shutdown_event: Optional[asyncio.Event] = None


def setup_logging(level: str) -> None:
    """Configure logging with the specified level."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def handle_shutdown(sig: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    logger = logging.getLogger(__name__)
    logger.info("Received shutdown signal (%s), stopping...", sig)
    if shutdown_event:
        shutdown_event.set()


class CommandHandler:
    """Handles DM commands from Signal users."""

    def __init__(
        self,
        frm_client: FRMClient,
        config: Config,
        server_client: Optional[ServerAPIClient] = None,
    ):
        self.frm = frm_client
        self.config = config
        self.server = server_client
        self.commands = {
            "help": self.cmd_help,
            "list": self.cmd_list,
            "players": self.cmd_list,
            "power": self.cmd_power,
            "status": self.cmd_status,
            "session": self.cmd_session,
            "settings": self.cmd_settings,
            "cheats": self.cmd_cheats,
            "saves": self.cmd_saves,
            "factory": self.cmd_factory,
            "trains": self.cmd_trains,
            "drones": self.cmd_drones,
            "vehicles": self.cmd_vehicles,
            "generators": self.cmd_generators,
            "storage": self.cmd_storage,
            "prod": self.cmd_prod,
            "sink": self.cmd_sink,
            "switches": self.cmd_switches,
            "connect": self.cmd_connect,
        }

    async def handle(self, text: str) -> str:
        """Process a command and return the response."""
        text = text.strip()

        # Handle commands with or without leading slash
        if text.startswith("/"):
            text = text[1:]

        parts = text.split(maxsplit=1)
        cmd = parts[0].lower() if parts else "help"
        args = parts[1] if len(parts) > 1 else ""

        # Help doesn't need server connection
        if cmd == "help":
            return self.cmd_help(args)

        handler = self.commands.get(cmd, self.cmd_unknown)
        result = await handler(args)

        # If server is offline, append status
        if not self.frm.is_online and cmd != "help":
            return f"[Server Offline] {self.frm.last_error}"

        return result

    def cmd_help(self, _: str) -> str:
        """Show available commands."""
        return (
            "Commands:\n"
            "  list - Online players\n"
            "  status - Server info\n"
            "  session - Session details\n"
            "  settings - Server settings\n"
            "  cheats - Cheat settings\n"
            "  saves - Recent saves\n"
            "  power - Power grid\n"
            "  generators - Power breakdown\n"
            "  factory - Building stats\n"
            "  prod - Production rates\n"
            "  storage [item] - Search storage\n"
            "  sink - AWESOME Sink\n"
            "  trains - Train status\n"
            "  drones - Drone status\n"
            "  vehicles - Vehicle status\n"
            "  switches - Power switches\n"
            "  connect - Server connection info"
        )

    async def cmd_unknown(self, args: str) -> str:
        """Handle unknown commands."""
        return "Unknown command. Type 'help' for available commands."

    async def cmd_list(self, _: str) -> str:
        """List online players."""
        players = await self.frm.get_players()
        if not players:
            return "No players online (or FRM unavailable)"

        lines = [f"Online players ({len(players)}):"]
        for p in players:
            ping_str = f" ({p.ping}ms)" if p.ping > 0 else ""
            lines.append(f"  - {p.name}{ping_str}")
        return "\n".join(lines)

    async def cmd_power(self, _: str) -> str:
        """Show power grid status."""
        power = await self.frm.get_power()
        if not power:
            return "Power data unavailable"

        status = "TRIPPED" if power.fuse_triggered else "OK"
        headroom = power.total_production - power.total_consumption

        lines = [
            f"Power Grid Status: {status}",
            f"  Production: {power.total_production:.1f} MW",
            f"  Consumption: {power.total_consumption:.1f} MW",
            f"  Headroom: {headroom:+.1f} MW",
            f"  Max Consumption: {power.max_consumption:.1f} MW",
        ]

        if power.battery_capacity > 0:
            lines.append(
                f"  Battery: {power.battery_percent:.0f}% ({power.battery_capacity:.1f} MWh)"
            )

        return "\n".join(lines)

    async def cmd_status(self, _: str) -> str:
        """Show server status."""
        session = await self.frm.get_session_info()
        if not session:
            if not self.frm.is_online:
                return "Server: OFFLINE"
            return "Session info unavailable"

        # Handle both single dict and list response
        if isinstance(session, list) and session:
            session = session[0]

        name = session.get("SessionName", "Unknown")
        playtime = session.get("TotalPlayDurationText", "Unknown")
        day = session.get("PassedDays", 0)
        is_day = "Day" if session.get("IsDay", True) else "Night"

        # Get online player count
        players = await self.frm.get_players()
        player_count = len(players)

        return (
            f"Server: {name} (ONLINE)\n"
            f"Players online: {player_count}\n"
            f"Day {day} ({is_day})\n"
            f"Playtime: {playtime}"
        )

    async def cmd_session(self, _: str) -> str:
        """Show detailed session info from dedicated server API."""
        if not self.server:
            return "Server API not configured"

        info = await self.server.get_session_info()
        if not info:
            return "Session info unavailable"

        # Format playtime
        hours = info.total_playtime_seconds // 3600
        mins = (info.total_playtime_seconds % 3600) // 60

        # Format tick rate with status
        tick_status = "OK" if info.tick_rate >= 25 else "SLOW"

        lines = [
            f"Session: {info.session_name}",
            f"Players: {info.players_online}/{info.player_limit}",
            f"Tech Tier: {info.tech_tier}",
            f"Phase: {info.game_phase}",
            f"Playtime: {hours}h {mins}m",
            f"Tick Rate: {info.tick_rate:.1f}/30 ({tick_status})",
        ]

        if info.is_paused:
            lines.append("Status: PAUSED")

        if info.active_schematic and info.active_schematic != "None":
            lines.append(f"Researching: {info.active_schematic}")

        return "\n".join(lines)

    async def cmd_settings(self, _: str) -> str:
        """Show server settings."""
        if not self.server:
            return "Server API not configured"

        options = await self.server.get_server_options()
        if not options:
            return "Settings unavailable"

        # Network quality mapping
        nq_map = {0: "Low", 1: "Medium", 2: "High", 3: "Ultra"}
        nq = nq_map.get(options["network_quality"], "Unknown")

        # Format autosave interval
        autosave_mins = options["autosave_interval"] // 60

        lines = [
            "Server Settings:",
            f"  Auto-Pause: {'Yes' if options['auto_pause'] else 'No'}",
            f"  Autosave Interval: {autosave_mins} min",
            f"  Autosave on Disconnect: {'Yes' if options['autosave_on_disconnect'] else 'No'}",
            f"  Network Quality: {nq}",
            f"  Seasonal Events: {'Yes' if options['seasonal_events'] else 'No'}",
        ]

        return "\n".join(lines)

    async def cmd_cheats(self, _: str) -> str:
        """Show cheat/advanced settings."""
        if not self.server:
            return "Server API not configured"

        settings = await self.server.get_advanced_settings()
        if not settings:
            return "Cheat settings unavailable"

        # Check if any cheats are enabled
        cheat_keys = [
            ("creative_mode", "Creative Mode"),
            ("god_mode", "God Mode"),
            ("flight_mode", "Flight Mode"),
            ("no_build_cost", "No Build Cost"),
            ("no_fuel_cost", "No Fuel Cost"),
            ("no_power", "No Power Required"),
            ("no_unlock_cost", "No Unlock Cost"),
            ("all_tiers_unlocked", "All Tiers Unlocked"),
            ("all_schematics_unlocked", "All Schematics Unlocked"),
            ("all_alt_recipes", "All Alt Recipes"),
            ("no_arachnids", "No Spiders"),
        ]

        enabled = [
            (label, settings[key]) for key, label in cheat_keys if settings.get(key)
        ]

        if not enabled:
            return "Cheats: None enabled"

        lines = ["Cheats Enabled:"]
        for label, _ in enabled:
            lines.append(f"  - {label}")

        return "\n".join(lines)

    async def cmd_saves(self, _: str) -> str:
        """Show recent save files."""
        if not self.server:
            return "Server API not configured"

        saves = await self.server.get_saves(limit=5)
        if not saves:
            return "No saves found"

        lines = ["Recent Saves:"]
        for s in saves:
            # Format playtime
            hours = s["playtime_seconds"] // 3600
            mins = (s["playtime_seconds"] % 3600) // 60

            # Parse save time (format: 2026.02.03-05.55.38)
            save_time = s["save_time"]
            if save_time:
                try:
                    date_part = save_time.split("-")[0]  # 2026.02.03
                    time_part = save_time.split("-")[1]  # 05.55.38
                    date_fmt = date_part.replace(".", "/")
                    time_fmt = time_part.replace(".", ":")[:5]
                    save_time = f"{date_fmt} {time_fmt}"
                except (IndexError, ValueError):
                    pass

            marker = "*" if s["is_current_session"] else " "
            modded = " [modded]" if s["is_modded"] else ""
            lines.append(f" {marker}{s['name']}: {hours}h{mins}m - {save_time}{modded}")

        lines.append("(* = current session)")
        return "\n".join(lines)

    async def cmd_factory(self, _: str) -> str:
        """Show factory statistics."""
        stats = await self.frm.get_factory_stats()
        if not stats:
            return "Factory data unavailable"

        return (
            f"Factory Status:\n"
            f"  Buildings: {stats['total_buildings']}\n"
            f"  Running: {stats['running']}\n"
            f"  Idle: {stats['idle']}\n"
            f"  Avg Efficiency: {stats['avg_efficiency']:.1f}%"
        )

    async def cmd_trains(self, _: str) -> str:
        """Show train status."""
        trains = await self.frm.get_trains()
        if not trains:
            return "No trains found"

        lines = [f"Trains ({len(trains)}):"]
        for t in trains:
            speed = f"{t['speed']:.0f} km/h" if t["speed"] > 0 else "stopped"
            lines.append(f"  - {t['name']}: {t['status']} ({speed})")
        return "\n".join(lines)

    async def cmd_drones(self, _: str) -> str:
        """Show drone status."""
        drones = await self.frm.get_drones()
        if not drones:
            return "No drones found"

        lines = [f"Drones ({len(drones)}):"]
        for d in drones:
            lines.append(f"  - {d['home']} -> {d['destination']}: {d['status']}")
        return "\n".join(lines)

    async def cmd_vehicles(self, _: str) -> str:
        """Show vehicle status."""
        vehicles = await self.frm.get_vehicles()
        if not vehicles:
            return "No vehicles found"

        lines = [f"Vehicles ({len(vehicles)}):"]
        for v in vehicles:
            status = "autopilot" if v["autopilot"] else "manual"
            speed = f"{v['speed']:.0f} km/h" if v["speed"] > 0 else "parked"
            lines.append(f"  - {v['type']}: {speed} ({status})")
        return "\n".join(lines)

    async def cmd_generators(self, _: str) -> str:
        """Show power generation breakdown."""
        gens = await self.frm.get_generators()
        if not gens:
            return "No generators found"

        lines = ["Power Generation:"]
        total_capacity = 0
        total_producing = 0

        for name, data in sorted(gens.items()):
            lines.append(
                f"  {name}: {data['count']}x ({data['producing']:.0f}/{data['capacity']:.0f} MW)"
            )
            total_capacity += data["capacity"]
            total_producing += data["producing"]

        lines.append(f"Total: {total_producing:.0f}/{total_capacity:.0f} MW")
        return "\n".join(lines)

    async def cmd_storage(self, args: str) -> str:
        """Search storage containers."""
        items = await self.frm.get_storage_items(args)
        if not items:
            if args:
                return f"No items matching '{args}' found in storage"
            return "No items in storage"

        # Limit to top 15 items
        items = items[:15]
        lines = [f"Storage{f' (matching: {args})' if args else ''}:"]
        for item in items:
            lines.append(f"  {item['name']}: {item['amount']:,}")

        if len(items) == 15:
            lines.append("  ...")
        return "\n".join(lines)

    async def cmd_prod(self, _: str) -> str:
        """Show production statistics."""
        stats = await self.frm.get_production_stats()
        if not stats:
            return "No production data"

        # Show top 10 items by net production
        stats = stats[:10]
        lines = ["Production (items/min):"]
        for s in stats:
            net = s["net"]
            sign = "+" if net >= 0 else ""
            lines.append(f"  {s['name']}: {sign}{net:.1f}")
        return "\n".join(lines)

    async def cmd_sink(self, _: str) -> str:
        """Show AWESOME Sink status."""
        sink = await self.frm.get_sink_stats()
        if not sink:
            return "Sink data unavailable"

        return (
            f"AWESOME Sink:\n"
            f"  Coupons: {sink['coupons']}\n"
            f"  Total Points: {sink['total_points']:,}\n"
            f"  Next Coupon: {sink['percent']:.1f}% ({sink['points_to_coupon']:,} points)"
        )

    async def cmd_switches(self, _: str) -> str:
        """Show power switch states."""
        switches = await self.frm.get_switches()
        if not switches:
            return "No power switches found"

        lines = [f"Power Switches ({len(switches)}):"]
        for s in switches:
            state = "ON" if s["is_on"] else "OFF"
            lines.append(f"  - {s['name']}: {state}")
        return "\n".join(lines)

    async def cmd_connect(self, _: str) -> str:
        """Show server connection info."""
        if not self.config.server_host:
            return "Server connection info not configured"

        lines = ["Server Connection Info:"]
        lines.append(f"  Host: {self.config.server_host}")
        lines.append(f"  Port: {self.config.server_port}")
        if self.config.server_password:
            lines.append(f"  Password: {self.config.server_password}")
        return "\n".join(lines)


class Bridge:
    """Main bridge class coordinating Signal and FRM communication."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        self.signal_client = SignalClient(
            api_url=config.signal_api_url,
            phone_number=config.signal_phone_number,
            group_id=config.signal_group_id,
        )

        self.frm_client = FRMClient(
            api_url=config.frm_api_url,
            access_token=config.frm_access_token,
        )

        # Server API client (optional)
        self.server_client: Optional[ServerAPIClient] = None
        if config.server_api_url and config.server_api_token:
            self.server_client = ServerAPIClient(
                api_url=config.server_api_url,
                api_token=config.server_api_token,
            )

        self.command_handler = CommandHandler(
            self.frm_client, config, self.server_client
        )

        # Track processed message timestamps to prevent duplicates
        self._processed_signal_timestamps: set[int] = set()
        self._max_tracked_timestamps = 1000

        # Track messages we've sent to the game to avoid echo
        self._sent_to_game: set[str] = set()
        self._max_sent_tracked = 100

    def _format_game_message(self, sender: str, message: str, msg_type: str) -> str:
        """Format a game message for Signal."""
        # Replace <PlayerName/> placeholder with actual sender name
        message = message.replace("<PlayerName/>", sender)

        # Convert shortcodes back to emojis for Signal display
        message = process_game_to_signal(message)

        if msg_type == "System":
            return f"[System] {message}"
        elif msg_type == "Ada":
            return f"[A.D.A.] {message}"
        else:
            return f"[{sender}] {message}"

    async def poll_game_chat(self) -> None:
        """Poll game chat and forward messages to Signal group."""
        if not self.config.signal_group_id:
            return

        messages = await self.frm_client.get_chat_messages()
        if not messages and not self.frm_client.is_online:
            # Server offline, skip silently
            return

        for msg in messages:
            # Skip messages from the bot itself to prevent loops
            if msg.sender == self.config.bot_name:
                continue

            # Skip messages we forwarded from Signal (prevent echo)
            msg_key = f"{msg.sender}:{msg.message}"
            if msg_key in self._sent_to_game:
                self._sent_to_game.discard(msg_key)
                continue

            formatted = self._format_game_message(
                msg.sender, msg.message, msg.message_type
            )
            await self.signal_client.send_to_group(formatted)
            self.logger.info("Game -> Signal: %s", formatted)

    async def poll_signal_messages(self) -> None:
        """Poll Signal messages and handle them appropriately."""
        messages = await self.signal_client.receive_messages_ws(
            timeout=self.config.poll_interval
        )

        for msg in messages:
            # Skip already processed messages
            if msg.timestamp in self._processed_signal_timestamps:
                continue

            self._processed_signal_timestamps.add(msg.timestamp)
            self._trim_processed_timestamps()

            if msg.is_group and self.signal_client.is_our_group(msg.group_id):
                # Group message -> forward to game chat
                await self._handle_group_message(msg)
            elif not msg.is_group:
                # DM -> handle as command
                await self._handle_dm(msg)

    async def _handle_group_message(self, msg: SignalMessage) -> None:
        """Handle a message from the Signal group."""
        # Send read receipt
        if msg.sender_uuid:
            await self.signal_client.send_read_receipt(msg.sender_uuid, msg.timestamp)

        # Check if it's a command (starts with /)
        if msg.text.startswith("/"):
            response = await self.command_handler.handle(msg.text)
            await self.signal_client.send_to_group(response)
            self.logger.info("Group command from %s: %s", msg.sender, msg.text)
            return

        # Process message for game: convert emojis to shortcodes, replace mentions, format attachments
        processed_text = process_signal_to_game(
            text=msg.text,
            attachments=msg.attachments,
            has_sticker=msg.has_sticker,
            mentions=msg.mentions,
        )

        # Skip if there's nothing to send after processing
        if not processed_text:
            return

        # Track this message to avoid echoing it back
        msg_key = f"{msg.sender}:{processed_text}"
        self._sent_to_game.add(msg_key)

        # Trim tracking set if needed
        if len(self._sent_to_game) > self._max_sent_tracked:
            # Remove oldest entries (just clear half)
            to_remove = list(self._sent_to_game)[: self._max_sent_tracked // 2]
            for key in to_remove:
                self._sent_to_game.discard(key)

        await self.frm_client.send_chat_message(
            message=processed_text,
            sender=msg.sender,
        )
        self.logger.info("Signal -> Game: [%s] %s", msg.sender, processed_text)

    async def _handle_dm(self, msg: SignalMessage) -> None:
        """Handle a direct message (command)."""
        self.logger.info("DM from %s: %s", msg.sender, msg.text)

        # Send read receipt
        if msg.sender_uuid:
            await self.signal_client.send_read_receipt(msg.sender_uuid, msg.timestamp)

        response = await self.command_handler.handle(msg.text)

        # Reply to the sender
        recipient = msg.sender_uuid or msg.sender
        await self.signal_client.send_dm(response, recipient)
        self.logger.info("DM reply to %s: %s", msg.sender, response[:50])

    def _trim_processed_timestamps(self) -> None:
        """Trim the processed timestamps set to prevent memory growth."""
        if len(self._processed_signal_timestamps) > self._max_tracked_timestamps:
            sorted_ts = sorted(self._processed_signal_timestamps)
            self._processed_signal_timestamps = set(
                sorted_ts[-self._max_tracked_timestamps // 2 :]
            )

    async def _game_chat_loop(self) -> None:
        """Continuous loop for polling game chat."""
        while not shutdown_event.is_set():
            try:
                await self.poll_game_chat()
                # Small delay between game chat polls
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error("Error in game chat loop: %s", e, exc_info=True)
                await asyncio.sleep(1)

    async def _signal_loop(self) -> None:
        """Continuous loop for polling Signal messages."""
        while not shutdown_event.is_set():
            try:
                await self.poll_signal_messages()
            except Exception as e:
                self.logger.error("Error in Signal loop: %s", e, exc_info=True)
                await asyncio.sleep(1)

    async def run(self) -> None:
        """Main event loop."""
        global shutdown_event
        shutdown_event = asyncio.Event()

        self.logger.info("Starting Satisfactory-Signal Bridge")
        self.logger.info("Signal API: %s", self.config.signal_api_url)
        self.logger.info("FRM API: %s", self.config.frm_api_url)
        if self.server_client:
            self.logger.info("Server API: %s", self.config.server_api_url)
        self.logger.info(
            "Group ID: %s", self.config.signal_group_id or "(none - DM only mode)"
        )
        self.logger.info("Poll interval: %s seconds", self.config.poll_interval)

        # Check API connectivity
        signal_ok = await self.signal_client.health_check()
        frm_ok = await self.frm_client.health_check()

        if not signal_ok:
            self.logger.warning(
                "Signal API is not reachable - will retry during operation"
            )
        if not frm_ok:
            self.logger.warning(
                "FRM API is not reachable - will retry during operation"
            )

        # Initialize FRM timestamp to avoid replaying old messages
        await self.frm_client.initialize_timestamp()

        self.logger.info("Bridge started, polling for messages (concurrent mode)...")

        try:
            # Run both listeners concurrently
            await asyncio.gather(
                self._game_chat_loop(),
                self._signal_loop(),
            )
        finally:
            # Clean up aiohttp sessions
            await self.frm_client.close()
            await self.signal_client.close()
            if self.server_client:
                await self.server_client.close()

        self.logger.info("Bridge stopped")


def main() -> int:
    """Application entry point."""
    config = Config.from_env()
    setup_logging(config.log_level)

    logger = logging.getLogger(__name__)

    # Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            logger.error("Configuration error: %s", error)
        return 1

    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    bridge = Bridge(config)

    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")

    return 0


if __name__ == "__main__":
    sys.exit(main())
