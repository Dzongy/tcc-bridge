#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# TCC Bridge V2.1 — BULLETPROOF INSTALLER (KAEL MOD)
# One-tap setup for permanent, self-healing bridge.
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[INSTALL]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}   $*"; }
fail() { echo -e "${RED}[FAIL]${NC}   $*"; exit 1; }

log "=========================================="
log " TCC Bridge V2.1 — Bulletproof Setup"
log "=========================================="

# 1. System Requirements
log "Installing core packages..."
pkg update -y || warn "pkg update failed, trying to continue..."
pkg install -y python nodejs git curl wget openssh termux-api termux-boot || fail "Package install failed"

# 2. PM2 Setup
log "Checking PM2..."
if ! command -v pm2 &> /dev/null; then
    npm install -g pm2 || fail "PM2 install failed"
fi

# 3. Directory Setup
BRIDGE_DIR="$HOME/tcc-bridge"
log "Setting up directory: $BRIDGE_DIR"
if [ ! -d "$BRIDGE_DIR" ]; then
    git clone https://github.com/Dzongy/tcc-bridge.git "$BRIDGE_DIR"
else
    cd "$BRIDGE_DIR" && git pull
fi
cd "$BRIDGE_DIR"

# 4. Python Dependencies
log "Installing Python dependencies..."
pip install requests || fail "Python deps failed"

# 5. Cloudflared setup
if ! command -v cloudflared &> /dev/null; then
    log "Installing cloudflared..."
    # Download latest for arm64
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ]; then
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O $PREFIX/bin/cloudflared
    else
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm -O $PREFIX/bin/cloudflared
    fi
    chmod +x $PREFIX/bin/cloudflared
fi

# 6. Termux:Boot setup
log "Configuring auto-start (Termux:Boot)..."
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-pm2 <<EOF
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
pm2 resurrect
EOF
chmod +x ~/.termux/boot/start-pm2

# 7. Start Bridge
log "Starting processes via PM2..."
pm2 delete tcc-bridge cloudflared state-pusher 2>/dev/null || true
pm2 start ecosystem.config.js
pm2 save

log "=========================================="
log " INSTALL COMPLETE! Bridge is active."
log "=========================================="
log "Monitor on ntfy: zenith-escape / tcc-zenith-hive"
log "Next step: Ensure Termux:Boot app is installed and launched."
log "=========================================="
