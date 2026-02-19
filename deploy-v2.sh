#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge v5.1 — ONE-TAP BULLETPROOF
set -e
echo "Starting TCC Bridge v5.1 Installation..."

pkg update -y && pkg install -y python git cloudflared termux-api nodejs
npm install -g pm2

mkdir -p ~/tcc-bridge
cd ~/tcc-bridge

# Fetch latest files from GitHub
curl -sSL https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/bridge.py -o bridge.py
curl -sSL https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/ecosystem.config.js -o ecosystem.config.js
curl -sSL https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/state-push.py -o state-push.py

# Boot setup
mkdir -p ~/.termux/boot
curl -sSL https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/boot-bridge.sh -o ~/.termux/boot/boot-bridge
chmod +x ~/.termux/boot/boot-bridge

# Start everything
pm2 start ecosystem.config.js
pm2 save

echo "Installation Complete! Bridge is bulletproof."
