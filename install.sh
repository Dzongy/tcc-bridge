#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "[TCC] Starting Bulletproof Bridge V2 Install..."

# 1. Update & Install Deps
pkg update -y && pkg upgrade -y
pkg install -y python nodejs termux-api cloudflared git

# 2. Setup Repo
cd ~
if [ -d "tcc-bridge" ]; then
    cd tcc-bridge && git pull
else
    git clone https://github.com/Dzongy/tcc-bridge.git
    cd tcc-bridge
fi

# 3. Install PM2
npm install -g pm2
pm2 install pm2-logrotate

# 4. Setup Termux:Boot
mkdir -p ~/.termux/boot/
cp termux-boot.sh ~/.termux/boot/tcc-bridge
chmod +x ~/.termux/boot/tcc-bridge

# 5. Start everything
pm2 start ecosystem.config.js
pm2 save

echo "[TCC] Bridge V2 Installed and Running via PM2!"
echo "[TCC] Open Termux:Boot app to ensure auto-start on reboot."
