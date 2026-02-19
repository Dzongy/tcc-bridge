#!/data/data/com.termux/files/usr/bin/bash
# ========================================================
# TCC BRIDGE V6 — BULLETPROOF INSTALLER
# ========================================================
# One-tap installation for the permanent bridge.
# Survives: Reboots, network drops, and more.
# ========================================================

set -e

echo "--- TCC Bridge V6: Initializing Bulletproof Infrastructure ---"

# 1. Update and install dependencies
echo "[1/5] Installing dependencies..."
pkg update -y
pkg install -y python nodejs termux-api coreutils lsof jq
npm install -g pm2

# 2. Setup directory structure
echo "[2/5] Setting up directories..."
mkdir -p $HOME/tcc/logs
mkdir -p $HOME/.termux/boot

# 3. Download/Update all scripts from GitHub
echo "[3/5] Fetching latest bulletproof scripts..."
REPO_RAW="https://raw.githubusercontent.com/Dzongy/tcc-bridge/main"

curl -sL $REPO_RAW/bridge.py -o $HOME/tcc/bridge.py
curl -sL $REPO_RAW/ecosystem.config.js -o $HOME/tcc/ecosystem.config.js
curl -sL $REPO_RAW/termux-boot.sh -o $HOME/.termux/boot/start-bridge.sh

chmod +x $HOME/tcc/bridge.py
chmod +x $HOME/.termux/boot/start-bridge.sh

# 4. Setup pm2
echo "[4/5] Configuring process management (PM2)..."
cd $HOME/tcc
pm2 delete all || true
pm2 start ecosystem.config.js
pm2 save

# 5. Finalize
echo "[5/5] Finalizing Bulletproof Bridge..."
termux-wake-lock

echo "========================================================"
echo "   TCC BRIDGE V6 INSTALLED SUCCESSFULLY"
echo "========================================================"
echo "Status: Bridge and Tunnel are running under PM2."
echo "Survivability: Auto-starts on boot via Termux:Boot."
echo "Public URL: https://zenith.cosmic-claw.com"
echo "Health: Check status with 'pm2 list'"
echo "Logs: View logs with 'pm2 logs tcc-bridge'"
echo "========================================================"
