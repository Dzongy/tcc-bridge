#!/bin/bash
# TCC BRIDGE V2 - ONE-TAP SETUP
echo "Installing TCC Bridge V2..."

pkg update && pkg upgrade -y
pkg install python nodejs-lts cloudflared termux-api termux-services -y
npm install -g pm2

mkdir -p ~/tcc-bridge
cd ~/tcc-bridge

# Download components
curl -O https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/bridge.py
curl -O https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/watchdog-v2.sh
curl -O https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/ecosystem.config.js
curl -O https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/state-push.py
curl -O https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/boot-bridge.sh

chmod +x *.py *.sh

# Setup Termux:Boot
mkdir -p ~/.termux/boot
cp boot-bridge.sh ~/.termux/boot/

# Start PM2
pm2 start ecosystem.config.js
pm2 save
pm2 startup

# Setup Cron for state-push
(crontab -l 2>/dev/null; echo "*/5 * * * * python3 ~/tcc-bridge/state-push.py") | crontab -

echo "SETUP COMPLETE. BRIDGE IS ONLINE."
