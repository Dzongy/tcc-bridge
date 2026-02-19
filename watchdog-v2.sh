#!/data/data/com.termux/files/usr/bin/bash
# BRIDGE V2 - INFINITE WATCHDOG
TUNNEL_ID="18ba1a49-fdf9-4a52-a27a-5250d397c5c5"

while true; do
  # 1. Start Tunnel if not running
  if ! pgrep -x "cloudflared" > /dev/null; then
    cloudflared tunnel run $TUNNEL_ID > ~/tcc-bridge/tunnel.log 2>&1 &
  fi

  # 2. Start PM2 if not running
  if ! pgrep -f "pm2" > /dev/null; then
    pm2 start ecosystem.config.js
  fi

  sleep 60
done
