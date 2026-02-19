#!/bin/bash
while true; do
  if ! curl -s http://localhost:8080/health > /dev/null; then
    pm2 restart bridge
    curl -d "Local Bridge Down - Restarted" https://ntfy.sh/tcc-zenith-hive
  fi
  if ! curl -s https://zenith.cosmic-claw.com/health > /dev/null; then
    pm2 restart tunnel
    curl -d "Public Tunnel Down - Restarting Cloudflared" https://ntfy.sh/tcc-zenith-hive
  fi
  sleep 60
done