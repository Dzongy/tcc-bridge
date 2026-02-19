#!/data/data/com.termux/files/usr/bin/bash
# Watchdog V3 — The Sentinel
# Monitoring Bridge, Tunnel, and reporting to ntfy.

TOPIC="tcc-zenith-hive"
NTFY_URL="https://ntfy.sh/$TOPIC"

alert() {
  curl -H "Title: Bridge Alert" -H "Priority: urgent" -H "Tags: warning,robot" -d "$1" "$NTFY_URL"
}

log() {
  echo "$(date): $1"
}

log "Sentinel V3 started..."

while true; do
  # Check Bridge
  if ! nc -z localhost 8765; then
    log "Bridge offline. Restarting..."
    pm2 restart tcc-bridge
    alert "Bridge V10.0 was offline. Sentinel restarted it."
  fi

  # Check Tunnel
  if ! pgrep -x "cloudflared" > /dev/null; then
    log "Cloudflared offline. Restarting..."
    pm2 restart cloudflared
    alert "Cloudflared tunnel was offline. Sentinel restarted it."
  fi

  sleep 60
done