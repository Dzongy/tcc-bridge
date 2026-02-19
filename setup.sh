#!/data/data/com.termux/files/usr/bin/sh
echo "Installing Bridge V2..."
pkg update && pkg upgrade -y
pkg install python nodejs-lts termux-api -y
npm install -g pm2
pip install requests
mkdir -p ~/.termux/boot
cp termux_boot.sh ~/.termux/boot/start-bridge
chmod +x ~/.termux/boot/start-bridge
pm2 start ecosystem.config.js
pm2 save
echo "Bridge V2 Installed and Running."
