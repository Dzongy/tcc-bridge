#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "--- TCC BRIDGE V2 BULLETPROOF INSTALLER ---"

# 1. Deps
pkg update -y && pkg upgrade -y
pkg install -y python nodejs termux-api cloudflared pm2 curl wget git

# 2. Cleanup & Prep
mkdir -p ~/tcc
cd ~/tcc

# 3. Fetch Files
echo "Fetching bridge files..."
curl -sSL https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/bridge.py -o bridge.py
curl -sSL https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/ecosystem.config.js -o ecosystem.config.js

# 4. Termux:Boot
mkdir -p ~/.termux/boot
curl -sSL https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/boot-bridge.sh -o ~/.termux/boot/boot-bridge.sh
chmod +x ~/.termux/boot/boot-bridge.sh

# 5. Start PM2
echo "Starting bridge services..."
pm2 delete all || true
pm2 start ecosystem.config.js
pm2 save
pm2 startup

# 6. Notify
curl -d "Bridge V2 Bulletproof Deployment Complete on zenith.cosmic-claw.com" ntfy.sh/tcc-zenith-hive

echo "--- DEPLOYMENT SUCCESSFUL ---"
echo "URL: zenith.cosmic-claw.com"
