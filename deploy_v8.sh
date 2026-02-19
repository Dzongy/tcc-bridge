#!/data/data/com.termux/files/usr/bin/bash
# ==========================================
# TCC BRIDGE V8 — PERMANENT INSTALLER
# ==========================================
set -e

echo "--- TCC Bridge V8: Building Bulletproof Sovereignty ---"

# 1. Install System Dependencies
echo "[1/6] Installing packages..."
pkg update -y
pkg install -y python nodejs termux-api coreutils lsof jq cloudflared
npm install -g pm2

# 2. Setup Directories
echo "[2/6] Organizing directories..."
mkdir -p $HOME/tcc/logs
mkdir -p $HOME/.termux/boot

# 3. Fetch Bulletproof Code
echo "[3/6] Fetching latest sovereignty code..."
REPO="https://raw.githubusercontent.com/Dzongy/tcc-bridge/main"
curl -sL $REPO/bridge.py -o $HOME/tcc/bridge.py
curl -sL $REPO/ecosystem.config.js -o $HOME/tcc/ecosystem.config.js
curl -sL $REPO/state-push.py -o $HOME/tcc/state-push.py
curl -sL $REPO/boot-bridge.sh -o $HOME/.termux/boot/start-bridge.sh

chmod +x $HOME/tcc/bridge.py
chmod +x $HOME/tcc/state-push.py
chmod +x $HOME/.termux/boot/start-bridge.sh

# 4. Process Management
echo "[4/6] Starting PM2 ecosystem..."
cd $HOME/tcc
pm2 start ecosystem.config.js
pm2 save

# 5. Boot Configuration
echo "[5/6] Enabling auto-start on reboot..."
termux-wake-lock
# Ensure Termux:Boot will run pm2 resurrect
echo "pm2 resurrect" >> $HOME/.termux/boot/start-bridge.sh

# 6. Final Confirmation
echo "[6/6] Bridge V8 deployed successfully!"
echo "Public URL: https://zenith.cosmic-claw.com"
pm2 status
