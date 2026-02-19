#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge v6.0 — ONE-TAP SETUP
set -euo pipefail

echo "--- TCC BRIDGE V6.0 INSTALLER ---"

# 1. Update & Install Deps
pkg update -y && pkg upgrade -y
pkg install -y python termux-api nodejs git cloudflared cronie

# 2. Setup Node/PM2
npm install -g pm2

# 3. Create Directories
mkdir -p ~/tcc/logs
mkdir -p ~/.termux/boot

# 4. Fetch Scripts from Repo (Assuming current directory is ~/tcc-bridge)
# Or we can just use the files already pushed.

# 5. Setup Termux Boot
cp boot-bridge.sh ~/.termux/boot/
chmod +x ~/.termux/boot/boot-bridge.sh

# 6. Start PM2
pm2 start ecosystem.config.js
pm2 save
pm2 startup

echo "--- INSTALL COMPLETE ---"
echo "Bridge is running via PM2."
echo "Cloudflare tunnel: zenith.cosmic-claw.com"
echo "Check health: curl http://localhost:8765/health"
