# Satisfactory-Signal Bridge

A bot that bridges Signal Messenger and Satisfactory game chat using the [Ficsit Remote Monitoring](https://ficsit.app/mod/FicsitRemoteMonitoring) mod.

## Features

- **Bidirectional chat** - Messages flow between Signal group and in-game chat
- **Bot commands** - Query server status, power, players, and more via DM or group
- **Dedicated Server API** - Session info, settings, saves from the server API
- **Lightweight** - 58MB distroless Docker image

## Quick Start (Docker)

```bash
docker run -d --name satisfactory-signal \
  -e SIGNAL_API_URL=http://signal-api:8080 \
  -e SIGNAL_PHONE_NUMBER=+1234567890 \
  -e SIGNAL_GROUP_ID=group.xxx \
  -e FRM_API_URL=http://game-server:8082 \
  -e FRM_ACCESS_TOKEN=your-token \
  ghcr.io/trthomps/satisfactory-signal:latest
```

## Commands

Send these via DM to the bot or in the bridged group chat:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/list` | Online players |
| `/status` | Server info (day/night, playtime) |
| `/session` | Session details (tier, phase, tick rate) |
| `/settings` | Server settings (auto-pause, autosave) |
| `/cheats` | Cheat settings if any enabled |
| `/saves` | Recent save files |
| `/power` | Power grid status |
| `/generators` | Power generation breakdown |
| `/factory` | Building stats |
| `/prod` | Production rates |
| `/storage [item]` | Search storage containers |
| `/sink` | AWESOME Sink stats |
| `/trains` | Train status |
| `/drones` | Drone status |
| `/vehicles` | Vehicle status |
| `/switches` | Power switch states |
| `/connect` | Server connection info |

## Installation

### Prerequisites

- [Ficsit Remote Monitoring](https://ficsit.app/mod/FicsitRemoteMonitoring) mod installed on your Satisfactory server
- [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) running with a registered number
- Docker (for containerized deployment) or Python 3.10+ (for local development)

### Option 1: Docker Compose

```yaml
services:
  satisfactory-signal:
    image: ghcr.io/trthomps/satisfactory-signal:latest
    restart: unless-stopped
    env_file: .env
```

### Option 2: Local Development

```bash
git clone https://github.com/trthomps/satisfactory-signal.git
cd satisfactory-signal
uv sync
cp .env.example .env
# Edit .env with your settings
uv run python main.py
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Signal API (required)
SIGNAL_API_URL=http://localhost:8080
SIGNAL_PHONE_NUMBER=+1234567890
SIGNAL_GROUP_ID=group.YOUR_GROUP_ID_HERE

# FRM API (required for game data)
FRM_API_URL=http://localhost:8082
FRM_ACCESS_TOKEN=your-frm-access-token

# Dedicated Server API (optional, for /session /settings /cheats /saves)
SERVER_API_URL=https://your.server.com:7777
SERVER_API_TOKEN=your-api-token

# Bot settings
POLL_INTERVAL=2.0
LOG_LEVEL=INFO
BOT_NAME=SignalBot

# Server connection info (for /connect command)
SERVER_HOST=your.server.com
SERVER_PORT=7777
SERVER_PASSWORD=yourpassword
```

### Getting a Signal Group ID

```bash
curl 'http://localhost:8080/v1/groups/+1234567890'
```

### Getting FRM Access Token

1. Open Satisfactory → Mods → Ficsit Remote Monitoring
2. Enable Web Server
3. Enable "Require API Key"
4. Copy the access token

### Getting Dedicated Server API Token

Generate a token via the server's web UI or API.

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SIGNAL_API_URL` | No | `http://localhost:8080` | signal-cli-rest-api URL |
| `SIGNAL_PHONE_NUMBER` | Yes | | Bot's Signal phone number |
| `SIGNAL_GROUP_ID` | No | | Group to bridge (base64) |
| `FRM_API_URL` | No | `http://localhost:8082` | FRM web server URL |
| `FRM_ACCESS_TOKEN` | Yes* | | FRM API token |
| `SERVER_API_URL` | No | | Dedicated Server API URL |
| `SERVER_API_TOKEN` | No | | Dedicated Server API token |
| `POLL_INTERVAL` | No | `2.0` | Polling interval (seconds) |
| `LOG_LEVEL` | No | `INFO` | Log level |
| `BOT_NAME` | No | `SignalBot` | Bot display name in game |
| `SERVER_HOST` | No | | Server host for /connect |
| `SERVER_PORT` | No | `7777` | Server port for /connect |
| `SERVER_PASSWORD` | No | | Server password for /connect |

\* Required if bridging game chat

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run linting
uv run ruff check .
uv run mypy --ignore-missing-imports *.py

# Build Docker image locally
docker build -t satisfactory-signal .
```

## License

MIT
