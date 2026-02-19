#!/data/data/com.termux/files/usr/bin/sh
# kael-watchdog.sh — PROCESS GUARDIAN
while true; do
  # Check Bridge
  if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "Bridge unresponsive, restarting..."
    pm2 restart kael-bridge
  fi
  # Check Cloudflare (placeholder for tunnel check)
  # cloudflared status ...
  sleep 60
done