#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Start SearXNG container if not running
if ! docker ps --format '{{.Names}}' | grep -q '^searxng$'; then
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d
fi

# Bootstrap venv if missing
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
    "$VENV_DIR/bin/playwright" install chromium
fi

exec "$VENV_DIR/bin/fastmcp" run "$SCRIPT_DIR/server.py"
