#!/data/data/com.termux/files/usr/bin/bash
echo "--- TCC BRIDGE V2 BULLETPROOF INSTALLER ---"
pkg update && pkg upgrade -y
pkg install -y python nodejs termux-api termux-services cloudflared
npm install pm2 -g
pip install requests

mkdir -p ~/.termux/boot
cp termux-boot.sh ~/.termux/boot/
chmod +x ~/.termux/boot/termux-boot.sh

pm2 start ecosystem.config.js
pm2 save
pm2 startup

echo "Bridge setup complete. Ensure Termux:Boot is installed and 'Display over other apps' is allowed."
