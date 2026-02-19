#!/data/data/com.termux/files/usr/bin/bash
# TCC BRIDGE V2 — ONE-TAP SOVEREIGNTY INSTALLER
echo "Starting TCC Bridge V2 Installation..."

# 1. Update and install dependencies
pkg update -y && pkg upgrade -y
pkg install -y python nodejs git termux-api cloudflared

# 2. Install PM2
npm install -g pm2

# 3. Setup repository
cd ~
if [ -d "tcc-bridge" ]; then
    cd tcc-bridge
    git pull origin main
else
    git clone https://github.com/Dzongy/tcc-bridge.git
    cd tcc-bridge
fi

# 4. Configure PM2
pm2 stop all || true
pm2 delete all || true
pm2 start ecosystem.config.js
pm2 save

# 5. Setup Boot persistence
bash setup_boot.sh

# 6. Notify
echo "Installation complete. Bridge is active."
python3 -c "import urllib.request; urllib.request.urlopen('https://ntfy.sh/tcc-zenith-hive', data=b'Bridge V2 Permanent Installation Complete. System is SOVEREIGN.', timeout=5)"

echo "DONE. Your bridge is now bulletproof."
