#!/bin/bash
# TCC Watchdog V2 - Guardians of the Bridge
while true; do
  if ! pgrep -f "bridge.py" > /dev/null; then
    pm2 restart bridge || python3 ~/tcc-bridge/bridge.py &
  fi
  if ! pgrep -f "cloudflared" > /dev/null; then
    pm2 restart tunnel || cloudflared tunnel run --token 18ba1a49-fdf9-4a52-a27a-5250d397c5c5 &
  fi
  sleep 60
done