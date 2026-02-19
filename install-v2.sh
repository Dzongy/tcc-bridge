#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge V2 — ONE-TAP BTLLETSROOF INSTALLER
# Run with: curl -sL https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/install-v2.sh | bash

echo "Starting TCC Bridge V2 Installation..."

# 1. Update and Install Core Tools
pkg update -y && pkg upgrade -y
pkg install -y python nodejs termux-api git curl cloudflared
npm install -g pm2

# 2. Setup Directory
mkdir -p ~/tcc-bridge
cd ~/tcc-bridge

# 3. Get Code
if [ -d ".git" ]; then
    git pull
else
    git clone https://github.com/Dzonyy/tcc-bridge.git .
fi

# 4. Setup Termux Boot
mkdir -p ~/.termux/boot
cp termux-boot.sh ~/.termux/boot/bridge-start.sh
chmod +x ~/.termux/boot/bridge-start.sh

# 5. Configuration (Interactive fallback)
if [ ! -f ~/.cloudflared/config.yml ]; then
    echo "WARNING: cloudflared not configured. Please run 'cloudflared tunnel login' manually."
fi

# 6. Start Everything
pm2 delete all
pm2 start ecosystem.config.js
pm2 save

echo "--- INSTALLATION COMPLETE ---"
echo "Bridge is running via PM2."
echo "Auto-start enabled via Termux:Boot."
curl -d "Bridge V2 Installation Complete on Phone" https://ntfy.sh/tcc-zenith-hive