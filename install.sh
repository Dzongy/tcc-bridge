#!/data/data/com.termux/files/usr/bin/bash
# TCC SOVEREIGN INSTALLER - BRIDGE V2
# The Ultimate One-Tap Sovereign Bridge Setup
# Author: KAEL / ZENITH
# Version: 1.1.0

set -e

echo "[*] TCC SOVEREIGN INSTALLER STARTING..."
echo "[*] Target: Bridge V2 Permanent Sovereignty"

# 1. System Prep
echo "[*] Updating system packages..."
pkg update -y && pkg upgrade -y
pkg install -y python nodejs git termux-api cloudflared jq curl

# 2. PM2 Setup
echo "[*] Installing PM2 for process management..."
npm install -g pm2

# 3. Directory Setup
echo "[*] Setting up directories..."
mkdir -p ~/.termux/boot/
mkdir -p ~/.cloudflared/
mkdir -p ~/tcc-bridge/

# 4. Repo Synchronization
echo "[*] Syncing Bridge V2 codebase..."
cd ~
if [ -d "tcc-bridge" ]; then
    cd tcc-bridge
    git fetch --all
    git reset --hard origin/main
else
    git clone https://github.com/Dzongy/tcc-bridge.git
    cd tcc-bridge
fi

# 5. Boot Persistence
echo "[*] Configuring Termux:Boot persistence..."
cp termux-boot.sh ~/.termux/boot/bridge-boot.sh
chmod +x ~/.termux/boot/bridge-boot.sh

# 6. PM2 Daemon Setup
echo "[*] Starting Bridge V2 services..."
pm2 stop all || true
pm2 delete all || true
pm2 start ecosystem.config.js
pm2 save

# 7. Final Check & Notification
echo "[*] Verifying services..."
pm2 status

echo "[*] Sending notification to Commander..."
curl -d "Sovereign Bridge V2 Installation Complete. System is now autonomous and bulletproof." https://ntfy.sh/tcc-zenith-hive

echo ""
echo "[+] SUCCESS: BRIDGE V2 IS ACTIVE."
echo "[+] Auto-start enabled via Termux:Boot."
echo "[+] Managed by PM2 with auto-restart."
echo "[+] Heartbeat active on ntfy: zenith-escape"
echo "[+] Sovereign domain: zenith.cosmic-claw.com"
echo ""
echo "Command: 'pm2 monit' to watch real-time."
