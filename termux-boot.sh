#!/data/data/com.termux/files/usr/bin/bash
# Termux:Boot script for TCC Bridge — BULLETPROOF EDITION
# Ensures pm2 starts and resurrects all processes on phone boot.

# Wait for network/system to settle
sleep 15

# Start pm2 and resurrect the bridge
pm2 resurrect || {
  cd ~/tcc-bridge
  pm2 start ecosystem.config.js
  pm2 save
}

# Send ntfy notification that phone rebooted
curl -d "TCC Bridge: Phone rebooted. Bridge services resurrected." ntfy.sh/tcc-zenith-hive
