#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge Watchdog v2 — keeps bridge.py alive FOREVER
# Handles: crashes, OOM kills, Termux restarts

BRIDGE_DIR="$HOME/tcc-bridge"
MAX_RAPID_RESTARTS=5
RAPID_WINDOW=60
RESTART_COUNT=0
LAST_RESTART=0

[ -f "$HOME/.bridge-env" ] && source "$HOME/.bridge-env"

echo "[WATCHDOG] Starting TCC Bridge Watchdog v2..."
echo "[WATCHDOG] Bridge dir: $BRIDGE_DIR"
echo "[WATCHDOG] PID: $$"

while true; do
    NOW=$(date +%s)
    
    # Track rapid restart detection
    ELAPSED=$((NOW - LAST_RESTART))
    if [ "$ELAPSED" -lt "$RAPID_WINDOW" ]; then
        RESTART_COUNT=$((RESTART_COUNT + 1))
    else
        RESTART_COUNT=0
    fi
    LAST_RESTART=$NOW
    
    # If crashing too fast, back off
    if [ "$RESTART_COUNT" -ge "$MAX_RAPID_RESTARTS" ]; then
        echo "[WATCHDOG] Too many rapid restarts. Backing off 60s..."
        curl -s -d '{"topic":"tcc-zenith-hive","title":"Bridge Watchdog Backoff","message":"Bridge crashed too many times. Waiting 60s.","priority":5,"tags":["warning","rotating_light"]}' https://ntfy.sh > /dev/null 2>&1
        sleep 60
        RESTART_COUNT=0
    fi
    
    # Pull latest code
    cd "$BRIDGE_DIR" 2>/dev/null && git pull origin main 2>/dev/null || true
    
    echo "[WATCHDOG] Starting bridge.py at $(date)..."
    python "$BRIDGE_DIR/bridge.py"
    EXIT_CODE=$?
    
    echo "[WATCHDOG] Bridge exited with code $EXIT_CODE at $(date)"
    echo "[WATCHDOG] Restarting in 3 seconds..."
    sleep 3
done