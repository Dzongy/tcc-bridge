#!/data/data/com.termux/files/usr/bin/bash
# TCC SOVEREIGN MASTER INSTALLER v1.2.0
set -e
echo "[*] INSTALLING SOVEREIGN BRIDGE V2..."
pkg update -y && pkg upgrade -y
pkg install -y python nodejs git termux-api cloudflared jq curl
npm install -g pm2
mkdir -p ~/.termux/boot/
cd ~
if [ -d "tcc-bridge" ]; then cd tcc-bridge && git fetch --all && git reset --hard origin/main; else git clone https://github.com/Dzongy/tcc-bridge.git && cd tcc-bridge; fi
cp boot_sovereign.sh ~/.termux/boot/tcc-bridge
chmod +x ~/.termux/boot/tcc-bridge
pm2 stop all || true
pm2 delete all || true
pm2 start ecosystem_sovereign.config.js
pm2 save
curl -d "Bridge V2 Sovereign Installation Successful" https://ntfy.sh/tcc-zenith-hive
echo "[+] SUCCESS. SYSTEM IS SOVEREIGN."
