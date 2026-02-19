#!/bin/bash
# TCC BRIDGE V2 - ONE-TAP SETUP
echo "Installing TCC Bridge V2..."

pkg update && pkg upgrade -y
pkg install python nodejs-lts cloudflared termux-api termux-services -y
npm install -g pm2

mkdir -p ~/tcc-bridge
cd ~/tcc-bridge

# Download components from V2 folder
BASE_URL="https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/v2"
curl -O "$BASE_URL/bridge.py"
curl -O "$BASE_URL/watchdog-v2.sh"
curl -O "$BASE_URL/ecosystem.config.js"
curl -O "$BASE_URL/state-push.py"
curl -O "$BASE_URL/boot-bridge.sh"

chmod +x *.py *.sh

# Setup Termux:Boot
mkdir -p ~/.termux/boot
cp boot-bridge.sh ~/.termux/boot/

# Start PM2pm2 start ecosystem.config.js 
pm2 save
pm2 startup

# Setup Cron for state-push (every 5 mins)
(crontab -l 2>/dev/null; echo "*/5 * * * * python3 ~/tcc-bridge/state-push.py") | crontab -

echo "SETUP COMPLETE. BRIDGE IS ONLINE."
