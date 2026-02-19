#!/data/data/com.termux/files/usr/bin/bash
# One-Tap Bridge V2 Bulletproof Installer
echo "Installing TCC Bridge V2..."
pkg update && pkg upgrade -y
pkg install python nodejs-lts termux-api cloudflared -y
pip install flask requests # if using flask, but we used stdlib
npm install -g pm2

mkdir -p ~/tcc-bridge
cd ~/tcc-bridge

# Pull code from repo (assuming git is installed)
pkg install git -y
git clone https://github.com/Dzongy/tcc-bridge.git . || git pull

# Setup Termux:Boot
mkdir -p ~/.termux/boot
cp termux-boot.sh ~/.termux/boot/start-bridge.sh
chmod +x ~/.termux/boot/start-bridge.sh

# Start everything
pm2 start ecosystem.config.js
pm2 save
pm2 startup

echo "Bridge V2 Installation Complete. Bulletproof mode active."
