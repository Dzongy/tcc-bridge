#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge — Termux:Boot Script
# This file goes in ~/.termux/boot/boot-bridge.sh
# Runs automatically when phone restarts and Termux:Boot is installed.

# Wait for network to be available
sleep 10

# Source environment
[ -f "$HOME/.bridge-env" ] && source "$HOME/.bridge-env"

BRIDGE_DIR="$HOME/tcc-bridge"
CF_DIR="$HOME/.cloudflared"
LOG="$HOME/boot-bridge.log"

echo "[$(date)] Boot script starting..." >> "$LOG"

# Pull latest code silently
cd "$BRIDGE_DIR" 2>/dev/null && git pull origin main >> "$LOG" 2>&1 || true

# Kill any stale processes
pkill -f 'python.*bridge.py' 2>/dev/null || true
pkill -f cloudflared 2>/dev/null || true
sleep 2

# Start watchdog (which starts bridge.py with auto-restart)
nohup bash "$HOME/watchdog-v2.sh" >> "$HOME/watchdog.log" 2>&1 &
echo "[$(date)] Watchdog started (PID: $!)" >> "$LOG"

# Start cloudflared tunnel
if [ -f "$CF_DIR/config.yml" ]; then
    nohup cloudflared tunnel --config "$CF_DIR/config.yml" run >> "$HOME/cloudflared.log" 2>&1 &
    echo "[$(date)] cloudflared started (PID: $!)" >> "$LOG"
else
    echo "[$(date)] WARNING: No cloudflared config found!" >> "$LOG"
fi

# Start cron daemon
crond 2>/dev/null || true

# Wait and verify
sleep 5
if curl -s http://localhost:8080/health | grep -q '"status"'; then
    echo "[$(date)] Bridge ONLINE - boot complete" >> "$LOG"
    curl -s -d '{"topic":"tcc-zenith-hive","title":"Bridge Boot Complete","message":"Phone restarted. Bridge v5.0 auto-started and ONLINE.","priority":3,"tags":["rocket","check"]}' https://ntfy.sh > /dev/null 2>&1
else
    echo "[$(date)] Bridge may still be starting..." >> "$LOG"
    curl -s -d '{"topic":"tcc-zenith-hive","title":"Bridge Boot Warning","message":"Phone restarted. Bridge starting but not yet responding.","priority":4,"tags":["warning"]}' https://ntfy.sh > /dev/null 2>&1
fi