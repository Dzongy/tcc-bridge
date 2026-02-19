#!/data/data/com.termux/files/usr/bin/bash
# TCC Watchdog v2
while true; do
  if ! pm2 describe tcc-bridge > /dev/null; then
    pm2 start ecosystem.config.js
  fi
  sleep 60
done
