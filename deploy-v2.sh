#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge v6.0 — ONE-TAP PERMANENT SETUP
set -euo pipefail
echo "Starting TCC Bridge v6.0 Installation..."

# Install Deps
pkg update -y && pkg upgrade -y
pkg install -y python termux-api nodejs git cloudflared cronie

# Setup Directories
mkdir -p ~/tcc/logs
mkdir -p ~/.termux/boot

# Install PM2
npm install -g pm2

# Setup Cloudflared (assume cert/config exists or use UUID)
# UUID is 18ba1a49-fdf9-4a52-a27a-5250d397c5c5

# Setup Boot script
cat <<EOF > ~/.termux/boot/start-tcc.sh
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
pm2 resurrect
cloudflared tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5 &
EOF
chmod +x ~/.termux/boot/start-tcc.sh

# Start services
pm2 start ecosystem.config.js
pm2 save
pm2 startup

echo "TCC Bridge v6.0 Installation Complete!"
curl -d "Bridge V6 Installation Complete on Device." https://ntfy.sh/tcc-zenith-hive
