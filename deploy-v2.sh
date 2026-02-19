#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

echo "--- TCC BRIDGE V7 BULLETPROOF SETUP ---"

# 1. Install packages
pkg update -y
pkg install -y python git cloudflared termux-api nodejs
npm install -g pm2

# 2. Setup directory
mkdir -p ~/tcc-bridge
cd ~/tcc-bridge

# 3. Setup boot script
mkdir -p ~/.termux/boot
cp termux-boot.sh ~/.termux/boot/
chmod +x ~/.termux/boot/termux-boot.sh

# 4. Setup PM2
pm2 start ecosystem.config.js
pm2 save

echo "SETUP COMPLETE."
