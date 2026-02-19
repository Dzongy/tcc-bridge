#!/data/data/com.termux/files/usr/bin/bash
# BRIDGE V2 INSTALLER
set -e
termux-wake-lock
pkg update -y && pkg upgrade -y
pkg install -y python nodejs termux-api git cloudflared cronie
npm install -g pm2
cd ~
[ -d "tcc-bridge" ] || git clone https://github.com/Dzongy/tcc-bridge.git
cd tcc-bridge && git pull
mkdir -p ~/.termux/boot
cp termux-boot.sh ~/.termux/boot/
chmod +x ~/.termux/boot/termux-boot.sh
pm2 delete all || true
pm2 start ecosystem.config.js
pm2 save
pm2 startup
echo "SETUP COMPLETE. Status: pm2 status"