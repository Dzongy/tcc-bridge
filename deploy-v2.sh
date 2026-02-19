#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# TCC Bridge v5.0 — ONE-TAP PERMANENT SETUP
# Run once in Termux: bash deploy-v2.sh
# After this, bridge survives EVERYTHING.
# ============================================================
set -e

echo "============================================================"
echo "  TCC BRIDGE v5.0 — PERMANENT INSTALLATION"
echo "  This will make the bridge UNKILLABLE."
echo "============================================================"
echo ""

BRIDGE_DIR="$HOME/tcc-bridge"
BOOT_DIR="$HOME/.termux/boot"
CF_DIR="$HOME/.cloudflared"
TUNNEL_UUID="18ba1a49-fdf9-4a52-a27a-5250d397c5c5"

# ── Step 1: Install dependencies ──
echo "[1/8] Installing dependencies..."
pkg update -y 2>/dev/null || true
pkg install -y python git cloudflared termux-api cronie 2>/dev/null || true
pip install requests flask 2>/dev/null || true
echo "  Done."

# ── Step 2: Clone/update repo ──
echo "[2/8] Getting latest code..."
if [ -d "$BRIDGE_DIR" ]; then
    cd "$BRIDGE_DIR" && git pull origin main 2>/dev/null || true
else
    cd "$HOME" && git clone https://github.com/Dzongy/tcc-bridge.git
fi
echo "  Done."

# ── Step 3: Setup Cloudflare tunnel config ──
echo "[3/8] Configuring Cloudflare tunnel..."
mkdir -p "$CF_DIR"

# Only write config if cert exists or create placeholder
if [ ! -f "$CF_DIR/config.yml" ]; then
    cat > "$CF_DIR/config.yml" << 'CFEOF'
tunnel: 18ba1a49-fdf9-4a52-a27a-5250d397c5c5
credentials-file: /data/data/com.termux/files/home/.cloudflared/18ba1a49-fdf9-4a52-a27a-5250d397c5c5.json

ingress:
  - hostname: zenith.cosmic-claw.com
    service: http://localhost:8080
  - service: http_status:404
CFEOF
    echo "  Config written. NOTE: You need the credentials JSON file."
else
    echo "  Config already exists."
fi
echo "  Done."

# ── Step 4: Setup Termux:Boot auto-start ──
echo "[4/8] Setting up Termux:Boot (survives phone restart)..."
mkdir -p "$BOOT_DIR"
cp "$BRIDGE_DIR/boot-bridge.sh" "$BOOT_DIR/boot-bridge.sh"
chmod 755 "$BOOT_DIR/boot-bridge.sh"
echo "  Boot script installed."
echo "  IMPORTANT: Open Termux:Boot app once to activate it!"

# ── Step 5: Setup cron for health push ──
echo "[5/8] Setting up health cron..."
# Start crond if not running
crond 2>/dev/null || true

# Add cron job for state push every 5 minutes
CRON_LINE="*/5 * * * * cd $BRIDGE_DIR && python state-push.py >> $HOME/state-push.log 2>&1"
(crontab -l 2>/dev/null | grep -v "state-push.py"; echo "$CRON_LINE") | crontab -
echo "  Cron job installed."

# ── Step 6: Setup watchdog ──
echo "[6/8] Installing watchdog..."
cp "$BRIDGE_DIR/watchdog-v2.sh" "$HOME/watchdog-v2.sh"
chmod 755 "$HOME/watchdog-v2.sh"
echo "  Watchdog ready."

# ── Step 7: Create env file ──
echo "[7/8] Setting up environment..."
if [ ! -f "$HOME/.bridge-env" ]; then
    cat > "$HOME/.bridge-env" << 'ENVEOF'
export BRIDGE_AUTH="amos-bridge-2026"
export BRIDGE_PORT="8080"
export NTFY_TOPIC="tcc-zenith-hive"
export SUPABASE_URL="https://vbqbbziqleymxcyesmky.supabase.co"
export SUPABASE_KEY=""
ENVEOF
    echo "  Environment file created at ~/.bridge-env"
    echo "  Add your SUPABASE_KEY there if you want state push."
else
    echo "  Environment file already exists."
fi

# ── Step 8: Start everything NOW ──
echo "[8/8] Starting bridge..."
source "$HOME/.bridge-env" 2>/dev/null || true

# Kill any existing bridge
pkill -f 'python.*bridge.py' 2>/dev/null || true
sleep 1

# Start bridge via watchdog (auto-restarts on crash)
nohup bash "$HOME/watchdog-v2.sh" > "$HOME/watchdog.log" 2>&1 &
echo "  Bridge watchdog started (PID: $!)"

# Start cloudflared
if pgrep -f cloudflared > /dev/null; then
    echo "  cloudflared already running."
else
    nohup cloudflared tunnel --config "$CF_DIR/config.yml" run > "$HOME/cloudflared.log" 2>&1 &
    echo "  cloudflared started (PID: $!)"
fi

# Wait and verify
sleep 3
echo ""
echo "============================================================"
echo "  VERIFICATION"
echo "============================================================"

# Check bridge
if curl -s http://localhost:8080/health | grep -q '"status"'; then
    echo "  [OK] Bridge: ONLINE on port 8080"
else
    echo "  [!!] Bridge: Starting up... check in 5 seconds"
fi

# Check cloudflared
if pgrep -f cloudflared > /dev/null; then
    echo "  [OK] Cloudflared: RUNNING"
else
    echo "  [!!] Cloudflared: NOT RUNNING — check credentials"
fi

# Check boot script
if [ -f "$BOOT_DIR/boot-bridge.sh" ]; then
    echo "  [OK] Boot script: INSTALLED"
else
    echo "  [!!] Boot script: MISSING"
fi

# Check cron
if crontab -l 2>/dev/null | grep -q "state-push"; then
    echo "  [OK] Health cron: ACTIVE"
else
    echo "  [!!] Health cron: NOT SET"
fi

echo ""
echo "============================================================"
echo "  SETUP COMPLETE"
echo "============================================================"
echo ""
echo "  The bridge is now PERMANENT. It will survive:"
echo "  - Phone restart (Termux:Boot)"
echo "  - Termux kill (watchdog auto-restart)"
echo "  - Bridge crash (watchdog + retry logic)"
echo "  - Tunnel crash (health monitor + auto-restart)"
echo "  - Network drop (cloudflared auto-reconnect)"
echo ""
echo "  Test it: curl https://zenith.cosmic-claw.com/health"
echo "  Logs: tail -f ~/bridge.log"
echo "  Watchdog: tail -f ~/watchdog.log"
echo ""
echo "  ONE MORE THING: Open the Termux:Boot app once!"
echo "  (Just open it — that activates boot-on-startup)"
echo "============================================================"
