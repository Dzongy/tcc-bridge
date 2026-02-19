#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge Sovereign V2 — Deployment Script
# curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/deploy-v2.sh | bash

echo "Starting Sovereign V2 Deployment..."

# 1. Update Packages
pkg update -y && pkg upgrade -y
pkg install -y python nodejs-lts git cloudflared termux-api cronie curl

# 2. Install PM2
npm install -g pm2

# 3. Setup Repo
cd $HOME
if [ -d "tcc-bridge" ]; then
  cd tcc-bridge && git pull
else
  git clone https://github.com/Dzongy/tcc-bridge.git
  cd tcc-bridge
fi

# 4. Permissions
chmod +x *.sh *.py

# 5. Termux Boot Setup
mkdir -p ~/.termux/boot
cp boot-bridge.sh ~/.termux/boot/
chmod +x ~/.termux/boot/boot-bridge.sh

# 6. Start Services
pm2 start ecosystem.config.js
pm2 save
pm2 startup

echo "Deployment Complete. Bridge Sovereign V2 is active."
