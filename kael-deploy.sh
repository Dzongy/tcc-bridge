#!/data/data/com.termux/files/usr/bin/sh
# kael-deploy.sh — ONE-TAP SETUP
echo "🚀 Starting Kael Bridge V2 Deployment..."

# Install dependencies
pkg update && pkg upgrade -y
pkg install python python-pip nodejs-lts termux-api -y
pip install requests
npm install -g pm2

# Setup directories
mkdir -p ~/tcc-bridge
mkdir -p ~/.termux/boot

# Download scripts
cd ~/tcc-bridge
curl -O https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/kael-bridge-final.py
curl -O https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/kael-boot-bridge.sh
curl -O https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/kael-ecosystem.config.js
curl -O https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/kael-watchdog.sh
curl -O https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/kael-state-push.py

chmod +x *.sh *.py

# Setup boot
cp kael-boot-bridge.sh ~/.termux/boot/

# Start everything
pm2 start kael-ecosystem.config.js
pm2 save

echo "✅ Deployment Complete. Bridge is running on port 8080."
echo "Check status with: pm2 status"
