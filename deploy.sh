#!/bin/bash
# AMOS Bridge v2 Deploy Script
# Run this in Termux: bash deploy.sh
# Or: cd ~/tcc-bridge && git pull && bash deploy.sh

set -e

BRIDGE_DIR="$HOME"
REPO_DIR="$HOME/tcc-bridge"

echo "[AMOS] Deploying Bridge v2..."

# Kill any existing bridge
pkill -f 'python.*bridge.py' 2>/dev/null || true
sleep 1

# Copy bridge.py to home dir
cp "$REPO_DIR/bridge.py" "$BRIDGE_DIR/bridge.py"
echo "[AMOS] bridge.py copied to $BRIDGE_DIR"

# Start bridge in background
cd "$BRIDGE_DIR"
nohup python bridge.py > bridge.log 2>&1 &
BRIDGE_PID=$!
echo "[AMOS] Bridge started (PID: $BRIDGE_PID)"

# Wait and verify
sleep 2
if curl -s http://localhost:8080/health | grep -q '"ok"'; then
    echo "[AMOS] Bridge v2 ONLINE - health check passed"
else
    echo "[AMOS] WARNING: Bridge health check failed. Check bridge.log"
fi

# Check if cloudflared is running
if pgrep -f cloudflared > /dev/null; then
    echo "[AMOS] cloudflared already running - tunnel should reconnect automatically"
else
    echo "[AMOS] Starting cloudflared tunnel..."
    nohup cloudflared tunnel --url http://localhost:8080 > cloudflared.log 2>&1 &
    sleep 3
    echo "[AMOS] cloudflared started. Check cloudflared.log for tunnel URL"
    echo "[AMOS] Look for: https://xxxxx.trycloudflare.com"
fi

echo "[AMOS] Deploy complete!"
