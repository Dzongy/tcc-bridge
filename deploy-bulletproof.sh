#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge V2 - Bulletproof Setup
set -e
info() { echo -e "\033[0;36m[INFO]\033[0m $1"; }

info "Updating packages..."
pkg update && pkg install python nodejs-lts termux-api cloudflared wget -y

info "Installing PM2..."
npm install pm2 -g

mkdir -p ~/tcc
mkdir -p ~/.termux/boot
cd ~/tcc

info "Pulling latest files from Dzongy/tcc-bridge..."
wget -O bridge.py https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/bridge.py
wget -O cloudflared_monitor.py https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/cloudflared_monitor.py
wget -O ecosystem.config.js https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/ecosystem.config.js
wget -O boot-bridge.sh https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/boot-bridge.sh

cp boot-bridge.sh ~/.termux/boot/boot-bridge.sh
chmod +x ~/.termux/boot/boot-bridge.sh
chmod +x bridge.py cloudflared_monitor.py

info "Starting PM2 ecosystem..."
pm2 start ecosystem.config.js
pm2 save

info "Setup complete! Cloudflare Tunnel 18ba1a49-fdf9-4a52-a27a-5250d397c5c5 is active."
