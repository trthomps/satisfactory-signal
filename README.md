# Satisfactory-Signal Bridge

A Python bot that bridges Signal Messenger and Satisfactory game chat using the Ficsit Remote Monitoring (FRM) mod's API.

## Features

- **Bidirectional messaging**: Messages flow between Signal and Satisfactory in both directions
- **Player name prefixing**: Game messages show player names in Signal, Signal messages show sender names in-game
- **Message deduplication**: Prevents message loops and duplicate processing
- **Graceful error handling**: Continues operation when APIs are temporarily unavailable

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker and Docker Compose
- Satisfactory with the [Ficsit Remote Monitoring](https://ficsit.app/mod/FicsitRemoteMonitoring) mod installed
- A Signal account with a registered phone number

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/trthomps/satisfactory-signal.git
cd satisfactory-signal
```

### 2. Install dependencies with uv

```bash
uv sync
```

### 3. Set up signal-cli-rest-api

Start the Signal API container:

```bash
docker compose up -d
```

### 4. Register or link your Signal number

**Option A: Register a new number**

```bash
# Request verification code
curl -X POST 'http://localhost:8080/v1/register/+1234567890'

# Verify with the code you received
curl -X POST 'http://localhost:8080/v1/register/+1234567890/verify/123456'
```

**Option B: Link to an existing Signal account**

```bash
# Get QR code link
curl 'http://localhost:8080/v1/qrcodelink?device_name=satisfactory-bridge'
```

Scan the QR code with your Signal app (Settings -> Linked Devices).

### 5. Configure the bot

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Your registered Signal phone number
SIGNAL_PHONE_NUMBER=+1234567890

# Either use a group ID or recipient numbers
SIGNAL_GROUP_ID=base64groupid==
# OR
SIGNAL_RECIPIENTS=+1234567891,+1234567892

# FRM API settings (check FRM mod settings in-game for the URL)
FRM_API_URL=http://localhost:8082
FRM_ACCESS_TOKEN=your-token-from-frm-settings
```

### 6. Configure FRM in Satisfactory

1. Open Satisfactory and load your save
2. Press Escape -> Mods -> Ficsit Remote Monitoring
3. Enable the Web Server
4. Note the port (default is 8080, but you may need to change it if it conflicts)
5. Enable "Require API Key" and copy the access token to your `.env` file

## Usage

Run the bot:

```bash
uv run python main.py
```

Or use the installed script:

```bash
uv run satisfactory-signal-bridge
```

### Running as a service (systemd)

Create `/etc/systemd/system/satisfactory-signal.service`:

```ini
[Unit]
Description=Satisfactory Signal Bridge
After=network.target docker.service

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/satisfactory-signal
ExecStart=/path/to/.local/bin/uv run python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable satisfactory-signal
sudo systemctl start satisfactory-signal
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `SIGNAL_API_URL` | `http://localhost:8080` | URL of signal-cli-rest-api |
| `SIGNAL_PHONE_NUMBER` | *required* | Your Signal phone number |
| `SIGNAL_GROUP_ID` | | Signal group ID (base64) |
| `SIGNAL_RECIPIENTS` | | Comma-separated phone numbers |
| `FRM_API_URL` | `http://localhost:8082` | URL of FRM web server |
| `FRM_ACCESS_TOKEN` | *required* | FRM API access token |
| `POLL_INTERVAL` | `2.0` | Seconds between polling |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `BOT_NAME` | `SignalBot` | Name used to identify bot messages |

## Troubleshooting

### Signal API not responding

1. Check if the container is running: `docker compose ps`
2. Check container logs: `docker compose logs signal-cli-rest-api`
3. Verify the phone number is registered: `curl http://localhost:8080/v1/about`

### FRM API not responding

1. Verify Satisfactory is running with the FRM mod
2. Check the FRM port in-game (Mods -> Ficsit Remote Monitoring)
3. Test the endpoint: `curl http://localhost:8082/getChatMessages`

### Messages not being sent to Satisfactory

1. Verify your FRM access token is correct
2. Check that "Require API Key" is enabled in FRM settings
3. Test sending directly:
   ```bash
   curl -X POST 'http://localhost:8082/sendChatMessage' \
     -H 'Content-Type: application/json' \
     -H 'X-FRM-Authorization: your-token' \
     -d '{"message": "Test"}'
   ```

### Getting a Signal Group ID

List your groups:

```bash
curl 'http://localhost:8080/v1/groups/+1234567890'
```

The group ID will be in base64 format.

## Development

Install dev dependencies:

```bash
uv sync --all-extras
```

Run linting:

```bash
uv run ruff check .
uv run mypy .
```

## License

MIT
