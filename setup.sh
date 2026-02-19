#!/data/data/com.termux/files/usr/bin/bash
# TCC BRIDGE V6 - THE SOVEREIGN ONE-TAP
set -e
echo "[AMOS] Building Sovereign Bridge..."
pkg update -y && pkg upgrade -y
pkg install -y python nodejs-lts git cloudflared termux-api termux-services
npm install -g pm2
mkdir -p ~/.termux/boot
[ -d "$HOME/tcc-bridge" ] || git clone https://github.com/Dzongy/tcc-bridge.git "$HOME/tcc-bridge"
cd "$HOME/tcc-bridge" && git pull origin main
cp bridge.py ecosystem.config.js ~/
cp termux-boot.sh ~/.termux/boot/start-bridge.sh
chmod +x ~/bridge.py ~/.termux/boot/start-bridge.sh
pm2 start ~/ecosystem.config.js && pm2 save && pm2 startup
echo "[AMOS] SOVEREIGN BRIDGE ONLINE."
