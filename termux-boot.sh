#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge — Bulletproof Auto-Start
# This script goes in ~/.termux/boot/
termux-wake-lock
sleep 30
# Start pm2 if not running, or resurrect
if pm2 list | grep -q "online"; then
  echo "PM2 already running"
else
  pm2 resurrect || {
    cd ~/tcc-bridge
    pm2 start ecosystem.config.js
    pm2 save
  }
fi
curl -d "Bridge v6 Resurrected on Boot" https://ntfy.sh/tcc-zenith-hive