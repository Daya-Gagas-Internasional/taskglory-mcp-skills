#!/usr/bin/env bash
#
# TaskGlory SSE Listener — Setup Script
#
# Script ini membantu setup auto-reply listener untuk Hermes Agent + TaskGlory.
# Jalankan: bash setup.sh
#
# Yang dilakukan:
#   1. Cek prerequisites (hermes, python3, MCP taskglory)
#   2. Copy listener script ke ~/.hermes/scripts/
#   3. Ambil token dari ~/.hermes/config.yaml
#   4. Resolve hermes binary path
#   5. Generate launchd plist (macOS) atau systemd service (Linux)
#   6. Load service
#
set -e

echo "=== TaskGlory SSE Listener Setup ==="
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LISTENER_SRC="$SCRIPT_DIR/taskglory_sse_listener.py"
HERMES_SCRIPTS_DIR="$HOME/.hermes/scripts"
LISTENER_DEST="$HERMES_SCRIPTS_DIR/taskglory_sse_listener.py"

# ── 1. Prerequisites ──────────────────────────────────────────────

echo "[1/6] Checking prerequisites..."

if ! command -v python3 &>/dev/null; then
    echo "  ERROR: python3 not found. Install Python 3.10+ first."
    exit 1
fi
echo "  python3: $(python3 --version)"

# Find hermes binary
HERMES_BIN="${HERMES_BIN:-$(command -v hermes 2>/dev/null || echo "$HOME/.local/bin/hermes")}"
if [ ! -f "$HERMES_BIN" ]; then
    echo "  ERROR: hermes binary not found at $HERMES_BIN"
    echo "  Set HERMES_BIN env var: export HERMES_BIN=/path/to/hermes"
    exit 1
fi
echo "  hermes: $HERMES_BIN"

# Check MCP taskglory
if ! "$HERMES_BIN" mcp test taskglory &>/dev/null 2>&1; then
    echo "  WARNING: MCP taskglory test failed. Run: $HERMES_BIN mcp test taskglory"
    echo "  Continue anyway? (y/N)"
    read -r response
    [ "$response" != "y" ] && exit 1
fi
echo "  MCP taskglory: OK"

# ── 2. Copy listener script ───────────────────────────────────────

echo ""
echo "[2/6] Copying listener script..."
mkdir -p "$HERMES_SCRIPTS_DIR"
cp "$LISTENER_SRC" "$LISTENER_DEST"
chmod +x "$LISTENER_DEST"
echo "  Copied: $LISTENER_DEST"

# ── 3. Get token ──────────────────────────────────────────────────

echo ""
echo "[3/6] Getting TaskGlory PAT token..."

CONFIG_FILE="$HOME/.hermes/config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "  ERROR: $CONFIG_FILE not found. Configure MCP taskglory first:"
    echo "    $HERMES_BIN mcp add taskglory https://dev.taskglory.com/api/mcp"
    exit 1
fi

TOKEN=$(grep -oE 'tgpat_[a-f0-9]+' "$CONFIG_FILE" | head -1)
if [ -z "$TOKEN" ]; then
    echo "  ERROR: No tgpat_ token found in $CONFIG_FILE"
    echo "  Get your PAT from TaskGlory web → Settings → Personal Access Tokens"
    echo "  Then add to config.yaml under mcp_servers.taskglory.headers.Authorization: Bearer tgpat_xxx"
    exit 1
fi
echo "  Token found: ${TOKEN:0:10}...${TOKEN: -4}"

# ── 4. Set hermes path in listener ────────────────────────────────

echo ""
echo "[4/6] Setting hermes path in listener..."
# The listener already uses HERMES_BIN env var with fallback.
# For launchd/systemd, we set it in the service file.
echo "  Hermes path: $HERMES_BIN"
echo "  (Will be set via HERMES_BIN env var in service file)"

# ── 5. Generate + load service ────────────────────────────────────

echo ""
echo "[5/6] Setting up persistent service..."

OS_TYPE="$(uname -s)"
case "$OS_TYPE" in
    Darwin)
        PLIST_PATH="$HOME/Library/LaunchAgents/com.hermes.taskglory-sse.plist"
        PLIST_DIR="$(dirname "$PLIST_PATH")"
        mkdir -p "$PLIST_DIR"

        cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hermes.taskglory-sse</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(command -v python3)</string>
        <string>$LISTENER_DEST</string>
        <string>$TOKEN</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HERMES_BIN</key>
        <string>$HERMES_BIN</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HERMES_SCRIPTS_DIR/sse_listener_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$HERMES_SCRIPTS_DIR/sse_listener_stderr.log</string>
    <key>WorkingDirectory</key>
    <string>$HERMES_SCRIPTS_DIR</string>
</dict>
</plist>
EOF
        echo "  Plist: $PLIST_PATH"

        # Unload if already loaded
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        # Load
        launchctl load "$PLIST_PATH"
        echo "  Loaded: launchctl load OK"

        # Verify
        sleep 2
        if launchctl list | grep -q "com.hermes.taskglory-sse"; then
            echo "  Status: running"
        else
            echo "  WARNING: service not showing in launchctl list"
            echo "  Check: cat $HERMES_SCRIPTS_DIR/sse_listener_stderr.log"
        fi
        ;;
    Linux)
        SERVICE_DIR="$HOME/.config/systemd/user"
        SERVICE_PATH="$SERVICE_DIR/taskglory-sse.service"
        mkdir -p "$SERVICE_DIR"

        cat > "$SERVICE_PATH" << EOF
[Unit]
Description=TaskGlory SSE Auto-Reply Listener
After=network.target

[Service]
Type=simple
ExecStart=$(command -v python3) $LISTENER_DEST $TOKEN
Restart=always
RestartSec=3
Environment=HERMES_BIN=$HERMES_BIN

[Install]
WantedBy=default.target
EOF
        echo "  Service: $SERVICE_PATH"

        systemctl --user daemon-reload
        systemctl --user enable --now taskglory-sse
        echo "  Enabled: systemctl --user enable --now taskglory-sse"

        # Verify
        sleep 2
        if systemctl --user is-active --quiet taskglory-sse; then
            echo "  Status: running"
        else
            echo "  WARNING: service not active"
            echo "  Check: systemctl --user status taskglory-sse"
        fi
        ;;
    *)
        echo "  ERROR: Unsupported OS: $OS_TYPE"
        echo "  Run listener manually: python3 $LISTENER_DEST $TOKEN &"
        exit 1
        ;;
esac

# ── 6. Verify ─────────────────────────────────────────────────────

echo ""
echo "[6/6] Verifying..."
sleep 3

LOG_FILE="$HERMES_SCRIPTS_DIR/sse_listener.log"
if [ -f "$LOG_FILE" ]; then
    LAST_LINE=$(tail -1 "$LOG_FILE")
    echo "  Log: $LOG_FILE"
    echo "  Last: $LAST_LINE"
    if echo "$LAST_LINE" | grep -q "Connected"; then
        echo "  SSE: CONNECTED"
    else
        echo "  SSE: waiting for connection... (check log in a few seconds)"
    fi
else
    echo "  Log file not yet created. Check in a few seconds:"
    echo "  tail -f $LOG_FILE"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Listener is running. Test it:"
echo "  1. Open TaskGlory web (dev.taskglory.com)"
echo "  2. Comment on a task where the agent is assigned/mentioned"
echo "  3. Check: tail -f $LOG_FILE"
echo ""
echo "Manage service:"
echo "  macOS:   launchctl list | grep taskglory-sse"
echo "           launchctl unload $PLIST_PATH  (stop)"
echo "           launchctl load $PLIST_PATH    (start)"
echo "  Linux:   systemctl --user status taskglory-sse"
echo "           systemctl --user stop taskglory-sse"
echo "           systemctl --user start taskglory-sse"
echo ""
echo "Logs:"
echo "  $LOG_FILE              (listener log)"
echo "  $HERMES_SCRIPTS_DIR/sse_listener_stderr.log  (errors)"