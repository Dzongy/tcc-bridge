#!/data/data/com.termux/files/usr/bin/bash
# deploy-v2.sh
# Master setup script for TCC Bridge V2 on Termux
# Run this once to fully configure the bridge environment

set -e

echo "========================================="
echo "  TCC Bridge V2 - Deployment Script"
echo "========================================="
echo ""

# ── 1. Update package lists ──────────────────────────────────────────────────
echo "[1/8] Updating package lists..."
pkg update -y && pkg upgrade -y

# ── 2. Install system dependencies ───────────────────────────────────────────
echo "[2/8] Installing system dependencies..."
pkg install -y python nodejs cloudflared termux-api coreutils debianutils

# ── 3. Install PM2 globally via npm ──────────────────────────────────────────
echo "[3/8] Installing PM2 globally..."
npm install -g pm2

# ── 4. Clone the repository ───────────────────────────────────────────────────
echo "[4/8] Setting up repository..."
mkdir -p ~/tcc

if [ ! -d "$HOME/tcc/tcc-bridge" ]; then
  echo "  Cloning Dzongy/tcc-bridge into ~/tcc/tcc-bridge..."
  git clone https://github.com/Dzongy/tcc-bridge.git ~/tcc/tcc-bridge
else
  echo "  Repository already exists at ~/tcc/tcc-bridge — skipping clone."
  echo "  Pulling latest changes instead..."
  git -C ~/tcc/tcc-bridge pull
fi

# Copy the ecosystem config and boot script into the repo directory
cp -f "$(dirname "$0")/ecosystem.config.js" ~/tcc/tcc-bridge/ecosystem.config.js || true
cp -f "$(dirname "$0")/boot-bridge.sh"      ~/tcc/tcc-bridge/boot-bridge.sh      || true

# ── 5. Setup Termux:Boot ──────────────────────────────────────────────────────
echo "[5/8] Configuring Termux:Boot..."
mkdir -p ~/.termux/boot
cp -f ~/tcc/tcc-bridge/boot-bridge.sh ~/.termux/boot/boot-bridge.sh
chmod +x ~/.termux/boot/boot-bridge.sh
echo "  boot-bridge.sh installed to ~/.termux/boot/"

# ── 6. Setup cron job for state-push.py (backup metrics) ─────────────────────
echo "[6/8] Configuring cron job for state-push.py (every 10 minutes)..."
# Install cronie if not already present
pkg install -y cronie 2>/dev/null || true

# Ensure crond is running
if ! pgrep -x crond > /dev/null 2>&1; then
  crond
fi

CRON_JOB="*/10 * * * * python3 $HOME/tcc/tcc-bridge/state-push.py >> $HOME/tcc/tcc-bridge/state-push.log 2>&1"
# Add cron job only if it doesn't already exist
( crontab -l 2>/dev/null | grep -v 'state-push.py' ; echo "$CRON_JOB" ) | crontab -
echo "  Cron job registered: $CRON_JOB"

# ── 7. Start PM2 with the ecosystem config ────────────────────────────────────
echo "[7/8] Starting PM2 processes..."
cd ~/tcc/tcc-bridge
pm2 start ecosystem.config.js

pm2 save
pm2 startup 2>&1 | tail -5

# ── 8. Final notifications ────────────────────────────────────────────────────
echo "[8/8] Finalising..."
echo ""
echo "========================================="
echo "  TCC Bridge V2 deployed successfully!"
echo "  Processes managed by PM2:"
pm2 list
echo "========================================="

# Notify ntfy topic
curl -s -X POST \
  -H "Title: TCC Bridge V2 Deployed" \
  -H "Priority: high" \
  -H "Tags: white_check_mark,bridge" \
  -d "TCC Bridge V2 has been deployed and started on $(hostname) at $(date)." \
  https://ntfy.sh/tcc-zenith-hive || echo "  [warn] ntfy notification failed (non-fatal)"

echo ""
echo "All done. Bridge is live. "
