#!/data/data/com.termux/files/usr/bin/bash
echo "🚀 Installing TCC Bridge V10.0 (Bulletproof)..."

# Dependencies
pkg update && pkg upgrade -y
pkg install python python-pip nodejs cloudflared termux-api coreutils debianutils nmap -y
pip install requests

# PM2
npm install -g pm2

# Setup Repo
mkdir -p ~/tcc
cd ~/tcc
if [ ! -d "tcc-bridge" ]; then
    git clone https://github.com/Dzongy/tcc-bridge.git
fi
cd tcc-bridge
git pull origin main
chmod +x *.sh

# Setup Termux:Boot
mkdir -p ~/.termux/boot
cp boot-bridge.sh ~/.termux/boot/
chmod +x ~/.termux/boot/boot-bridge.sh

# Setup Cron for state-push (runs every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * python3 ~/tcc/tcc-bridge/state-push.py") | crontab -

# Start via PM2
pm2 start ecosystem.config.js
pm2 save
pm2 startup

echo "✅ BRIDGE V10.0 DEPLOYED."
echo "Commander, simply run 'pm2 list' to check status."
curl -d "Bridge V10.0 Deployment Complete on $HOSTNAME" https://ntfy.sh/tcc-zenith-hive