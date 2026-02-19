#!/data/data/com.termux/files/usr/bin/bash
# Bridge V2 — One-Tap Setup
set -e

echo "[TCC] Starting Bridge V2 Setup..."

# 1. Dependencies
pkg update -y && pkg upgrade -y
pkg install -y python nodejs termux-api cloudflared

# 2. Python Packages
pip install requests

# 3. PM2
npm install -g pm2

# 4. Clone/Update Repo
mkdir -p ~/tcc-bridge
cd ~/tcc-bridge
# (Assuming repo is already cloned or we copy files here)

# 5. Boot Setup
mkdir -p ~/.termux/boot
cp termux-boot.sh ~/.termux/boot/start-tcc.sh
chmod +x ~/.termux/boot/start-tcc.sh

# 6. Start Stack
pm2 start ecosystem.config.js
pm2 save

echo "[TCC] Setup Complete. Bridge V2 is Online."
termux-toast "Bridge V2 Setup Complete"
