#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# TCC BRIDGE V2 — BULLETPROOF INSTALLER
# =============================================================================
# One-tap installation for the permanent bridge infrastructure.
# =============================================================================

set -e

echo "--- TCC Bridge V2: Initializing Bulletproof Infrastructure ---"

# 1. Update and install dependencies
echo "[1/6] Installing dependencies..."
pkg update -y
pkg install -y python nodejs termux-api coreutils lsof jq
npm install -g pm2

# 2. Setup directory structure
echo "[2/6] Setting up directories..."
mkdir -p $HOME/tcc/logs
mkdir -p $HOME/.termux/boot

# 3. Download/Update all scripts from GitHub
echo "[3/6] Fetching latest bulletproof scripts..."
REPO_RAW="https://raw.githubusercontent.com/Dzongy/tcc-bridge/main"

curl -sL $REPO_RAW/bridge.py -o $HOME/tcc/bridge.py
curl -sL $REPO_RAW/ecosystem.config.js -o $HOME/tcc/ecosystem.config.js
curl -sL $REPO_RAW/state-push.py -o $HOME/tcc/state-push.py
curl -sL $REPO_RAW/cloudflared_monitor.py -o $HOME/tcc/cloudflared_monitor.py
curl -sL $REPO_RAW/termux-boot.sh -o $HOME/.termux/boot/start-tcc.sh

chmod +x $HOME/tcc/*.py
chmod +x $HOME/.termux/boot/start-tcc.sh

# 4. Configure Environment
echo "[4/6] Configuring environment..."
if [ ! -f "$HOME/tcc/.env" ]; then
    cat <<EOF > $HOME/tcc/.env
BRIDGE_PORT=8080
BRIDGE_AUTH=
SUPABASE_URL=https://vbqbbziqleymxcyesmky.supabase.co
SUPABASE_KEY=sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm
NTFY_OPS_TOPIC=zenith-escape
NTFY_HIVE_TOPIC=tcc-zenith-hive
EOF
    echo "Created default .env file at ~/tcc/.env"
fi

# 5. Initialize PM2 Ecosystem
echo "[5/6] Starting PM2 ecosystem..."
cd $HOME/tcc
pm2 delete all || true
pm2 start ecosystem.config.js
pm2 save

# 6. Finalize Boot Setup
echo "[6/6] Finalizing Termux:Boot setup..."
# Ensure termux-wake-lock is active
termux-wake-lock

echo "============================================================================="
echo " INSTALLATION COMPLETE: BRIDGE V2 IS LIVE "
echo "============================================================================="
echo "1. Bridge: http://localhost:8080/health"
echo "2. Tunnel: zenith.cosmic-claw.com/health"
echo "3. Logs: tail -f ~/tcc/logs/bridge.log"
echo "============================================================================="
echo "NOTE: Ensure the 'Termux:Boot' app is installed and 'battery optimization' is DISABLED."
echo "============================================================================="
