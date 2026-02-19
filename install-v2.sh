#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# TCC Bridge V2 — One-Tap Install Script
# Run: bash install-v2.sh
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[INSTALL]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}   $*"; }
fail() { echo -e "${RED}[FAIL]${NC}   $*"; exit 1; }

log "======================================"
log " TCC Bridge V2 — Installer"
log "======================================"

# ── 1. Update pkg ──
log "Updating package lists..."
pkg update -y || warn "pkg update had issues, continuing..."

# ── 2. Core packages ──
log "Installing core packages..."
pkg install -y python nodejs git curl wget openssh termux-api || fail "Package install failed"

# ── 3. Python deps ──
log "Installing Python dependencies..."
pip install --quiet requests 2>&1 | tail -3

# ── 4. PM2 ──
log "Installing PM2..."
if ! command -v pm2 &>/dev/null; then
    npm install -g pm2 || fail "PM2 install failed"
    log "PM2 installed: $(pm2 --version)"
else
    log "PM2 already present: $(pm2 --version)"
fi

# ── 5. cloudflared ──
log "Installing cloudflared..."
if ! command -v cloudflared &>/dev/null; then
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ]; then
        CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
    elif [ "$ARCH" = "armv7l" ] || [ "$ARCH" = "armv8l" ]; then
        CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm"
    else
        CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    fi
    log "Downloading cloudflared for $ARCH..."
    curl -L "$CF_URL" -o "$PREFIX/bin/cloudflared" || fail "cloudflared download failed"
    chmod +x "$PREFIX/bin/cloudflared"
    log "cloudflared installed: $(cloudflared --version)"
else
    log "cloudflared already present: $(cloudflared --version)"
fi

# ── 6. Bridge directory ──
BRIDGE_DIR="$HOME/tcc-bridge"
log "Setting up bridge directory at $BRIDGE_DIR..."
mkdir -p "$BRIDGE_DIR"

# Copy files if we're running from the source dir
for f in bridge.py state-push.py ecosystem.config.js; do
    if [ -f "$(pwd)/$f" ]; then
        cp "$(pwd)/$f" "$BRIDGE_DIR/$f"
        log "Copied $f → $BRIDGE_DIR/$f"
    else
        warn "$f not found in $(pwd) — make sure to place it in $BRIDGE_DIR manually"
    fi
done

# ── 7. Termux:Boot setup ──
log "Setting up Termux:Boot..."
BOOT_DIR="$HOME/.termux/boot"
mkdir -p "$BOOT_DIR"
if [ -f "$(pwd)/boot-bridge.sh" ]; then
    cp "$(pwd)/boot-bridge.sh" "$BOOT_DIR/start-bridge.sh"
else
    # Generate it inline
    cat > "$BOOT_DIR/start-bridge.sh" << 'BOOTEOF'
#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge Boot Script
termux-wake-lock
sleep 12
cd /data/data/com.termux/files/home/tcc-bridge
pm2 resurrect || pm2 start ecosystem.config.js
pm2 save
BOOTEOF
fi
chmod +x "$BOOT_DIR/start-bridge.sh"
log "Boot script installed at $BOOT_DIR/start-bridge.sh"

# ── 8. .bridge-env ──
log "Creating $HOME/.bridge-env..."
cat > "$HOME/.bridge-env" << 'ENVEOF'
export BRIDGE_AUTH="amos-bridge-2026"
export BRIDGE_PORT="8080"
export DEVICE_ID="amos-arms"
export NTFY_TOPIC="tcc-zenith-hive"
export SUPABASE_URL="https://vbqbbziqleymxcyesmky.supabase.co"
export SUPABASE_KEY=""
ENVEOF
log ".bridge-env created — edit SUPABASE_KEY before starting!"

# Source it for this session
source "$HOME/.bridge-env" 2>/dev/null || true

# ── 9. Start everything ──
log "Starting PM2 processes..."
cd "$BRIDGE_DIR"
pm2 delete all 2>/dev/null || true
pm2 start ecosystem.config.js
pm2 save
pm2 startup 2>/dev/null || warn "pm2 startup not supported in Termux (use Termux:Boot instead)"

# ── 10. Status ──
log ""
log "======================================"
log " INSTALL COMPLETE"
log "======================================"
pm2 list
log ""
log "Bridge URL  : http://localhost:8080"
log "Health check: curl http://localhost:8080/health"
log "Logs        : pm2 logs bridge"
log ""
warn "ACTION REQUIRED: Edit $HOME/.bridge-env and set SUPABASE_KEY"
warn "Then: source ~/.bridge-env && pm2 restart bridge"
log "======================================"
