#!/bin/bash
# TCC Watchdog v2.0 - Kael Protocol
while true; do
  # Check Bridge
  if ! curl -s --max-time 5 http://localhost:8080/health > /dev/null; then
    echo "$(date) - Bridge DOWN. Restarting..." >> ~/watchdog.log
    pm2 restart bridge
    curl -d "Bridge DOWN - Auto-restarted" https://ntfy.sh/tcc-zenith-hive
  fi
  
  # Check Tunnel (cloudflared)
  # We check if the process is running at least
  if ! pgrep -x "cloudflared" > /dev/null; then
    echo "$(date) - Tunnel DOWN. Restarting..." >> ~/watchdog.log
    pm2 restart tunnel
    curl -d "Tunnel DOWN - Auto-restarted" https://ntfy.sh/tcc-zenith-hive
  fi

  sleep 60
done
