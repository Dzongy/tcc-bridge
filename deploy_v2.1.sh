#!/bin/bash
# TCC Bridge V2.1.0 - One-Tap Setup
# Author: Kael

echo "--- TCC Bridge V2.1.0 Installation ---"

# 1. System Packages
pkg update && pkg upgrade -y
pkg install python nodejs termux-api -y
npm install -g pm2

# 2. Cloudflared (assuming arm64 for Samsung)
if ! command -v cloudflared &> /dev/null
then
    echo "Installing cloudflared..."
    wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O $PREFIX/bin/cloudflared
    chmod +x $PREFIX/bin/cloudflared
fi

# 3. Directory Setup
mkdir -p ~/tcc-bridge
mkdir -p ~/.termux/boot
cd ~/tcc-bridge

# 4. Fetch Scripts
echo "Downloading scripts..."
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/bridge_v2.1.py -o bridge_v2.1.py
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/ecosystem_v2.1.js -o ecosystem_v2.1.js
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/boot_v2.1.sh -o boot_v2.1.sh
chmod +x bridge_v2.1.py boot_v2.1.sh

# 5. Boot Setup
cp boot_v2.1.sh ~/.termux/boot/boot_v2.1.sh
chmod +x ~/.termux/boot/boot_v2.1.sh

# 6. Launch
echo "Launching Bridge V2..."
termux-wake-lock
pm2 start ecosystem_v2.1.js
pm2 save
pm2 startup

echo "--- Setup Complete! ---"
echo "Check ntfy tcc-zenith-hive for status."
