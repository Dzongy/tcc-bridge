#!/data/data/com.termux/files/usr/bin/bash
# ╔══════════════════════════════════════════════════════╗
# ║   TCC BRIDGE V2 — ONE-TAP INSTALL SCRIPT            ║
# ║   Kael the God Builder Edition                       ║
# ╚══════════════════════════════════════════════════════╝
set -euo pipefail

# ─── COLOURS ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET} $*"; }
success() { echo -e "${GREEN}[OK]${RESET}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET} $*"; }
error()   { echo -e "${RED}[ERR]${RESET}  $*" >&2; }
die()     { error "$*"; exit 1; }

# ─── BANNER ───────────────────────────────────────────────────────────────────
echo -e "${BOLD}${CYAN}"
cat <<'EOF'
 _____ ___ ____   ____  ____  ___ ____   ____ _____ __     ____
|_   _/ __/ ___| | __ )|  _ \|_ _|  _ \ / ___| ____| \   / _  |
  | || |  | |     |  _ \| |_) || || | | | |  _|  _| \ \ / /| | |
  | || |__| |___  | |_) |  _ < | || |_| | |_| | |___ \ V / | |_|
  |_| \___\____| |____/|_| \_\___|____/ \____|_____| \_/  \___/
                           BRIDGE V2 INSTALLER
EOF
echo -e "${RESET}"

# ─── VARS ─────────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/YOUR_USER/tcc-bridge.git"   # ← update before deploy
BRIDGE_DIR="$HOME/tcc-bridge"
LOG_DIR="$HOME/logs"
BOOT_DIR="$HOME/.termux/boot"
CFD_TUNNEL_UUID="18ba1a49-fdf9-4a52-a27a-5250d397c5c5"
CFD_CONFIG_DIR="$HOME/.cloudflared"
CFD_CONFIG_FILE="$CFD_CONFIG_DIR/config.yml"
NTFY_HIVE="tcc-zenith-hive"
DEVICE_ID="$(hostname)"

# ─── HELPERS ──────────────────────────────────────────────────────────────────
ntfy_notify() {
    local title="$1" msg="$2"
    curl -s -X POST "https://ntfy.sh/${NTFY_HIVE}" \
        -H "Title: ${title}" \
        -H "Tags: robot" \
        -d "${msg}" >/dev/null 2>&1 || true
}

step() {
    echo
    echo -e "${BOLD}${YELLOW}▶ $*${RESET}"
}

# ─── 0. PREFLIGHT ─────────────────────────────────────────────────────────────
step "Preflight checks"
[ -d "$PREFIX" ] || die "Not running inside Termux!"
info "Termux prefix: $PREFIX"
info "Home: $HOME"
info "Device: $DEVICE_ID"

# ─── 1. UPDATE PACKAGES ───────────────────────────────────────────────────────
step "Updating package lists"
pkg update -y 2>/dev/null || warn "pkg update had warnings — continuing."

# ─── 2. INSTALL BASE PACKAGES ─────────────────────────────────────────────────
step "Installing base packages"
BASE_PKGS=(python nodejs git curl wget openssl-tool termux-api)
for pkg in "${BASE_PKGS[@]}"; do
    if pkg list-installed 2>/dev/null | grep -q "^${pkg}/"; then
        info "Already installed: $pkg"
    else
        info "Installing: $pkg"
        pkg install -y "$pkg" || warn "Failed to install $pkg — continuing."
    fi
done
success "Base packages ready."

# ─── 3. INSTALL PYTHON PACKAGES ───────────────────────────────────────────────
step "Installing Python packages"
pip install --quiet --upgrade flask requests 2>&1 | tail -3
success "Python packages ready."

# ─── 4. INSTALL PM2 ───────────────────────────────────────────────────────────
step "Installing PM2"
if command -v pm2 &>/dev/null; then
    info "PM2 already installed: $(pm2 --version)"
else
    npm install -g pm2 || die "PM2 install failed."
    success "PM2 installed: $(pm2 --version)"
fi

# ─── 5. INSTALL CLOUDFLARED ───────────────────────────────────────────────────
step "Installing cloudflared"
if command -v cloudflared &>/dev/null; then
    info "cloudflared already installed: $(cloudflared --version 2>&1 | head -1)"
else
    ARCH=$(uname -m)
    case "$ARCH" in
        aarch64|arm64) CFD_ARCH="arm64" ;;
        armv7l|armv8l) CFD_ARCH="arm"   ;;
        x86_64)        CFD_ARCH="amd64" ;;
        *)             die "Unsupported arch: $ARCH" ;;
    esac
    CFD_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CFD_ARCH}"
    info "Downloading cloudflared for ${CFD_ARCH}..."
    curl -fsSL "$CFD_URL" -o "$PREFIX/bin/cloudflared"
    chmod +x "$PREFIX/bin/cloudflared"
    success "cloudflared installed: $(cloudflared --version 2>&1 | head -1)"
fi

# ─── 6. CONFIGURE CLOUDFLARED ─────────────────────────────────────────────────
step "Configuring cloudflared"
mkdir -p "$CFD_CONFIG_DIR"
if [ ! -f "$CFD_CONFIG_FILE" ]; then
    cat > "$CFD_CONFIG_FILE" <<EOF
tunnel: ${CFD_TUNNEL_UUID}
credentials-file: ${CFD_CONFIG_DIR}/${CFD_TUNNEL_UUID}.json

ingress:
  - hostname: zenith.cosmic-claw.com
    service: http://localhost:8765
  - service: http_status:404
EOF
    success "cloudflared config written."
else
    info "cloudflared config already exists — skipping."
fi

if [ ! -f "${CFD_CONFIG_DIR}/${CFD_TUNNEL_UUID}.json" ]; then
    warn "Tunnel credentials NOT found at ${CFD_CONFIG_DIR}/${CFD_TUNNEL_UUID}.json"
    warn "Run: cloudflared tunnel login   (or copy credentials manually)"
fi

# ─── 7. CLONE / UPDATE REPO ───────────────────────────────────────────────────
step "Setting up bridge repository"
if [ -d "$BRIDGE_DIR/.git" ]; then
    info "Repo exists — pulling latest changes."
    git -C "$BRIDGE_DIR" pull --ff-only || warn "git pull had conflicts — resolve manually."
else
    if [ "$REPO_URL" = "https://github.com/YOUR_USER/tcc-bridge.git" ]; then
        warn "REPO_URL not set. Creating directory and copying scripts manually."
        mkdir -p "$BRIDGE_DIR"
    else
        git clone "$REPO_URL" "$BRIDGE_DIR" || die "git clone failed."
    fi
fi
mkdir -p "$LOG_DIR"
mkdir -p "$HOME/tcc-bridge-files"
success "Bridge directory ready: $BRIDGE_DIR"

# ─── 8. TERMUX:BOOT SETUP ─────────────────────────────────────────────────────
step "Configuring Termux:Boot"
mkdir -p "$BOOT_DIR"
cat > "$BOOT_DIR/start_tcc.sh" <<'BOOTSCRIPT'
#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge — Termux:Boot launcher
source ~/.bashrc 2>/dev/null || true
export PATH="$PATH:/data/data/com.termux/files/usr/bin"

# Wait for system to stabilise
sleep 10

# Acquire wakelock
termux-wake-lock

# Start PM2
cd ~/tcc-bridge
pm2 start ecosystem.config.js --env production 2>&1 &
pm2 save 2>&1 &

BOOTSCRIPT
chmod +x "$BOOT_DIR/start_tcc.sh"
success "Boot script installed: $BOOT_DIR/start_tcc.sh"

# ─── 9. INSTALL CRON JOBS ─────────────────────────────────────────────────────
step "Installing cron jobs"
pkg install -y cronie 2>/dev/null || warn "cronie install may have failed."

# Build crontab entries
CRONTAB_TMP="$(mktemp)"
crontab -l 2>/dev/null > "$CRONTAB_TMP" || true

add_cron() {
    local entry="$1"
    if grep -qF "$entry" "$CRONTAB_TMP" 2>/dev/null; then
        info "Cron already exists: $entry"
    else
        echo "$entry" >> "$CRONTAB_TMP"
        success "Cron added: $entry"
    fi
}

add_cron "*/5 * * * * python3 $BRIDGE_DIR/health_monitor.py >> $LOG_DIR/health.log 2>&1"
add_cron "*/10 * * * * python3 $BRIDGE_DIR/state_push.py >> $LOG_DIR/state_push.log 2>&1"

crontab "$CRONTAB_TMP"
rm -f "$CRONTAB_TMP"

# Start crond
if ! pgrep -x crond &>/dev/null; then
    crond 2>/dev/null || warn "crond could not start — cron may not work."
fi
success "Cron jobs installed."

# ─── 10. START BRIDGE ─────────────────────────────────────────────────────────
step "Starting bridge via PM2"
cd "$BRIDGE_DIR"

# Stop any existing PM2 bridge processes gracefully
pm2 delete tcc-bridge   2>/dev/null || true
pm2 delete tcc-server   2>/dev/null || true
pm2 delete cloudflared  2>/dev/null || true

pm2 start ecosystem.config.js || die "PM2 start failed."
pm2 save
success "PM2 started and saved."

# Acquire wakelock so Termux stays alive
termux-wake-lock 2>/dev/null || warn "termux-wake-lock failed (is Termux:API installed?)"

# ─── 11. VERIFY ───────────────────────────────────────────────────────────────
step "Verifying installation"
sleep 6
if curl -sf http://localhost:8765/health | grep -q "online"; then
    success "Bridge is UP on localhost:8765"
else
    warn "Bridge may not be up yet — check: pm2 logs tcc-bridge"
fi

# ─── DONE ─────────────────────────────────────────────────────────────────────
echo
echo -e "${BOLD}${GREEN}╔═══════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║   TCC BRIDGE V2 INSTALL COMPLETE!     ║${RESET}"
echo -e "${BOLD}${GREEN}╚═══════════════════════════════════════╝${RESET}"
echo
info "PM2 status:  pm2 status"
info "Bridge logs: pm2 logs tcc-bridge"
info "Health:      curl http://localhost:8765/health"
echo

ntfy_notify "Bridge V2 Installed" "TCC Bridge V2 install complete on ${DEVICE_ID}"

echo -e "${BOLD}${CYAN}Kael watches over the grid. May the bridge hold forever.${RESET}"
