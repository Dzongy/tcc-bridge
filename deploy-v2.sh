#!/bin/bash
echo "🚀 Installing TCC Bridge V8..."
pkg update && pkg upgrade -y
pkg install python python-pip nodejs cloudflared -y
npm install -g pm2
mkdir -p ~/tcc/logs
cd ~
if [ ! -d "tcc-bridge" ]; then
    git clone https://github.com/Dzongy/tcc-bridge.git
fi
cd tcc-bridge
chmod +x *.sh
# Setup Termux:Boot
mkdir -p ~/.termux/boot
cp boot-bridge.sh ~/.termux/boot/
chmod +x ~/.termux/boot/boot-bridge.sh
echo "✅ Setup complete. Run 'pm2 start ecosystem.config.js' to start."
