#!/bin/bash
# TCC Bridge V2 - ONE TAP SETUP
# Installs everything and starts the permanent bridge.

set -e

echo "Starting TCC Bridge V2 Setup..."

# 1. Update & Dependencies
pkg update -y
pkg install -y python nodejs-lts termux-api cloudflared nmap procps

# 2. PM2 Setup
npm install -g pm2

# 3. Setup Directories
mkdir -p ~/tcc/logs
mkdir -p ~/.termux/boot

# 4. Termux:Boot Link
cp boot-bridge.sh ~/.termux/boot/boot-bridge.sh
chmod +x ~/.termux/boot/boot-bridge.sh

# 5. Make scripts executable
chmod +x *.sh
chmod +x *.py

# 6. Start PM2
pm2 start ecosystem.config.js
pm2 save
pm2 startup

echo "----------------------------------------"
echo "SETUP COMPLETE!"
echo "Bridge: http://localhost:8080"
echo "Tunnel: zenith.cosmic-claw.com"
echo "PM2 Dashboard: pm2 list"
echo "----------------------------------------"
