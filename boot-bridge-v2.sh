#!/bin/bash
# Termux Boot Script for TCC Bridge V2
# Place in ~/.termux/boot/

# Wait for network
sleep 10

# Load environment
export PATH=$PATH:/data/data/com.termux/files/usr/bin

# Start Cloudflare Tunnel
cloudflared tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5 > ~/cloudflare.log 2>&1 &

# Start Bridge V2 via PM2
if command -v pm2 &> /dev/null
then
    pm2 resurrect || pm2 start ~/tcc-bridge/ecosystem-v2.config.js
else
    python ~/tcc-bridge/bridge-v2.py > ~/bridge-v2.log 2>&1 &
fi

# Start Guardian Watchdog V2
bash ~/tcc-bridge/watchdog-v2.sh &
