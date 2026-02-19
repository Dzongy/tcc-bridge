#!/data/data/com.termux/files/usr/bin/bash
# BRIDGE V2 ONE-TAP SETUP
set -e
echo "Starting Bulletproof Bridge V2 Setup..."

pkg update -y && pkg upgrade -y
pkg install -y python nodejs termux-api git cloudflared cronie
npm install -g pm2

# Clone or update repo
if [ -d "$HOME/tcc-bridge" ]; then
    cd "$HOME/tcc-bridge" && git pull
else
    git clone https://github.com/Dzongy/tcc-bridge.git "$HOME/tcc-bridge"
    cd "$HOME/tcc-bridge"
fi

# Set up Termux:Boot
mkdir -p "$HOME/.termux/boot"
cp boot-bridge.sh "$HOME/.termux/boot/"
chmod +x "$HOME/.termux/boot/boot-bridge.sh"

# Start with PM2
pm2 start ecosystem.config.js
pm2 save
pm2 startup

echo "SETUP COMPLETE. Bridge is running via PM2."
echo "Check status with: pm2 status"
