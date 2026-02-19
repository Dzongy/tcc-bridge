#!/data/data/com.termux/files/usr/bin/bash
echo "TCC BRIDGE V2 — ONE-TAP INSTALLER"

# 1. Install System Dependencies
pkg update -y && pkg upgrade -y
pkg install -y python nodejs termux-api curl git
npm install -g pm2

# 2. Setup Cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "Installing Cloudflared..."
    curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
    dpkg -i cloudflared.deb
    rm cloudflared.deb
fi

# 3. Setup Repository
cd $HOME
if [ ! -d "$HOME/tcc-bridge" ]; then
    git clone https://github.com/Dzongy/tcc-bridge.git
else
    cd tcc-bridge && git pull
fi

cd $HOME/tcc-bridge

# 4. Install Python Dependencies
pip install requests

# 5. Setup Termux:Boot
mkdir -p ~/.termux/boot
cp boot-bridge.sh ~/.termux/boot/tcc-bridge
chmod +x ~/.termux/boot/tcc-bridge

# 6. Initialize PM2
pm2 start ecosystem.config.js
pm2 save

echo "------------------------------------------------"
echo "INSTALLATION COMPLETE."
echo "Bridge is now running via PM2."
echo "Cloudflare tunnel started (check dashboard)."
echo "Health status: http://localhost:8080/health"
echo "------------------------------------------------"
