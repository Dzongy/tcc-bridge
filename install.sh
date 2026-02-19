#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# TCC Bridge V2 - One-Tap Installer
# Just run this script and everything will be set up automatically.
# =============================================================================

# --- Safety: stop on real errors but allow command failures we handle --------
set -euo pipefail

# ================================
# CONFIGURATION (edit if needed)
# ================================
BRIDGE_DIR="$HOME/tcc-bridge"
REPO_URL="https://github.com/YOUR_ORG/tcc-bridge.git"   # <-- UPDATE THIS
CLOUDFLARED_UUID="18ba1a49-fdf9-4a52-a27a-5250d397c5c5"
BRIDGE_PORT="8765"
DEVICE_ID="amos-arms"
NTFY_OPS_URL="https://ntfy.sh/zenith-escape"

# =============================================================================

# Colors for readable output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "\n${BLUE}===> $*${NC}"; }

# =============================================================================
# STEP 0: Welcome
# =============================================================================
clear
echo -e "${BLUE}"
echo "  âââââââââ âââââââ âââââââ     âââââââ âââââââ ââââââââââ  âââââââ ââââââââ"
echo "     ââââââââââââââââââââââ     âââââââââââââââââââââââââââââââââââ ââââââââ"
echo "     âââ   âââ     âââ          ââââââââââââââââââââââ  ââââââ  ââââââââââ"
echo "     âââ   âââ     âââ          ââââââââââââââââââââââ  ââââââ   âââââââââ"
echo "     âââ   ââââââââââââââââ     âââââââââââ  âââââââââââââââââââââââââââââââ"
echo "     âââ    âââââââ âââââââ     âââââââ âââ  âââââââââââââ  âââââââ ââââââââ"
echo -e "${NC}"
echo -e "${GREEN}  TCC Bridge V2 - One-Tap Installer${NC}"
echo    "  This will install and configure everything automatically."
echo    "  Estimated time: 2-5 minutes depending on your connection."
echo
read -rp "  Press ENTER to begin, or Ctrl+C to cancel... "
echo

# =============================================================================
# STEP 1: Update Termux packages
# =============================================================================
log_step "Step 1/9: Updating Termux package lists"
pkg update -y 2>/dev/null || apt-get update -y 2>/dev/null || log_warn "Package update had warnings (usually safe to ignore)"

# =============================================================================
# STEP 2: Install core dependencies
# =============================================================================
log_step "Step 2/9: Installing core packages (python, nodejs, git, curl)"
pkg install -y python nodejs git curl wget openssl-tool 2>/dev/null || {
  log_error "Failed to install core packages. Check your internet connection."
  exit 1
}
log_info "Core packages installed."

# =============================================================================
# STEP 3: Install PM2
# =============================================================================
log_step "Step 3/9: Installing PM2 (process manager)"
if command -v pm2 > /dev/null 2>&1; then
  log_info "PM2 already installed: $(pm2 --version)"
else
  npm install -g pm2 || {
    log_error "PM2 installation failed."
    exit 1
  }
  log_info "PM2 installed: $(pm2 --version)"
fi

# =============================================================================
# STEP 4: Install cloudflared
# =============================================================================
log_step "Step 4/9: Installing cloudflared"
if command -v cloudflared > /dev/null 2>&1; then
  log_info "cloudflared already installed: $(cloudflared --version 2>&1 | head -1)"
else
  ARCH=$(uname -m)
  CF_VERSION="2024.6.1"
  case "$ARCH" in
    aarch64|arm64)
      CF_URL="https://github.com/cloudflare/cloudflared/releases/download/${CF_VERSION}/cloudflared-linux-arm64"
      ;;
    armv7l|armv7)
      CF_URL="https://github.com/cloudflare/cloudflared/releases/download/${CF_VERSION}/cloudflared-linux-arm"
      ;;
    x86_64)
      CF_URL="https://github.com/cloudflare/cloudflared/releases/download/${CF_VERSION}/cloudflared-linux-amd64"
      ;;
    *)
      log_warn "Unknown arch $ARCH - attempting arm64 binary."
      CF_URL="https://github.com/cloudflare/cloudflared/releases/download/${CF_VERSION}/cloudflared-linux-arm64"
      ;;
  esac

  log_info "Downloading cloudflared from: $CF_URL"
  curl -fsSL "$CF_URL" -o "$PREFIX/bin/cloudflared" || {
    log_error "cloudflared download failed."
    exit 1
  }
  chmod +x "$PREFIX/bin/cloudflared"
  log_info "cloudflared installed: $(cloudflared --version 2>&1 | head -1)"
fi

# =============================================================================
# STEP 5: Clone or update the bridge repository
# =============================================================================
log_step "Step 5/9: Setting up bridge repository at $BRIDGE_DIR"

mkdir -p "$BRIDGE_DIR/logs"

if [[ -d "$BRIDGE_DIR/.git" ]]; then
  log_info "Repository exists. Pulling latest changes..."
  cd "$BRIDGE_DIR"
  git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || log_warn "Git pull had warnings - continuing with existing files."
else
  # If REPO_URL is placeholder, skip cloning and just ensure files exist
  if echo "$REPO_URL" | grep -q "YOUR_ORG"; then
    log_warn "REPO_URL is not configured. Skipping git clone."
    log_warn "Please manually place bridge.py and ecosystem.config.js in $BRIDGE_DIR"
  else
    log_info "Cloning repository..."
    git clone "$REPO_URL" "$BRIDGE_DIR" || {
      log_error "Git clone failed. Check REPO_URL in this script."
      exit 1
    }
  fi
fi

cd "$BRIDGE_DIR"

# Verify bridge.py exists
if [[ ! -f "$BRIDGE_DIR/bridge.py" ]]; then
  log_warn "bridge.py not found in $BRIDGE_DIR. Please copy it there before starting pm2."
else
  chmod +x "$BRIDGE_DIR/bridge.py"
  log_info "bridge.py found and made executable."
fi

# Verify ecosystem.config.js exists
if [[ ! -f "$BRIDGE_DIR/ecosystem.config.js" ]]; then
  log_warn "ecosystem.config.js not found in $BRIDGE_DIR. PM2 startup may fail."
else
  log_info "ecosystem.config.js found."
fi

# =============================================================================
# STEP 6: Set up Termux:Boot auto-start script
# =============================================================================
log_step "Step 6/9: Setting up Termux:Boot auto-start"

BOOT_DIR="$HOME/.termux/boot"
mkdir -p "$BOOT_DIR"

BOOT_SCRIPT="$BOOT_DIR/tcc-bridge"
cat > "$BOOT_SCRIPT" << 'BOOTSCRIPT_EOF'
#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge V2 - Termux:Boot auto-start script
# Runs automatically when the phone boots (requires Termux:Boot app)

# Wait for system to fully initialize
sleep 15

# Source profile to get correct PATH
source /data/data/com.termux/files/usr/etc/profile 2>/dev/null || true

# Acquire wakelock to prevent CPU sleep killing the bridge
termux-wake-lock 2>/dev/null || true

# Resurrect pm2 saved process list
pm2 resurrect 2>/dev/null || pm2 start /data/data/com.termux/files/home/tcc-bridge/ecosystem.config.js

# Save updated process list
pm2 save --force 2>/dev/null || true
BOOTSCRIPT_EOF

chmod +x "$BOOT_SCRIPT"
log_info "Termux:Boot script created at: $BOOT_SCRIPT"

# =============================================================================
# STEP 7: Set up health check cron-style via pm2 schedule (or reminder)
# =============================================================================
log_step "Step 7/9: Setting up health check script"

if [[ -f "$BRIDGE_DIR/health_check.sh" ]]; then
  chmod +x "$BRIDGE_DIR/health_check.sh"
  log_info "health_check.sh made executable."
else
  log_warn "health_check.sh not found in $BRIDGE_DIR - skipping."
fi

# =============================================================================
# STEP 8: Start everything with PM2
# =============================================================================
log_step "Step 8/9: Starting bridge and cloudflared with PM2"

if [[ -f "$BRIDGE_DIR/ecosystem.config.js" ]]; then
  # Stop existing processes cleanly if running
  pm2 stop tcc-bridge 2>/dev/null || true
  pm2 stop cloudflared 2>/dev/null || true
  pm2 delete tcc-bridge 2>/dev/null || true
  pm2 delete cloudflared 2>/dev/null || true

  # Start fresh from ecosystem config
  pm2 start "$BRIDGE_DIR/ecosystem.config.js" || {
    log_error "PM2 start failed. Check ecosystem.config.js and bridge.py."
    exit 1
  }

  # Save so pm2 resurrect works on boot
  pm2 save --force
  log_info "PM2 processes started and saved."
else
  log_warn "No ecosystem.config.js found - skipping PM2 start."
  log_warn "Run 'pm2 start $BRIDGE_DIR/ecosystem.config.js' manually when ready."
fi

# =============================================================================
# STEP 9: Verify and report
# =============================================================================
log_step "Step 9/9: Verifying installation"

sleep 5  # Give pm2 a moment to spin up processes

echo
log_info "PM2 process status:"
pm2 list 2>/dev/null || true

echo
# Quick health check against local server
if curl -sf --max-time 10 "http://localhost:${BRIDGE_PORT}/health" > /dev/null 2>&1; then
  log_info "â Bridge is RESPONDING on localhost:${BRIDGE_PORT}/health"
else
  log_warn "Bridge not yet responding on localhost:${BRIDGE_PORT} - it may still be starting up."
  log_warn "Wait 10 seconds and run: curl http://localhost:${BRIDGE_PORT}/health"
fi

# Send success notification
curl -sf \
  -H "Title: ð¢ TCC Bridge V2 Installed" \
  -H "Priority: high" \
  -H "Tags: rocket,white_check_mark" \
  -d "Bridge V2 installation complete on device: ${DEVICE_ID}.\nPort: ${BRIDGE_PORT}\nCloudflared UUID: ${CLOUDFLARED_UUID}\nRun 'pm2 logs' to see live output." \
  "$NTFY_OPS_URL" > /dev/null 2>&1 || true

echo
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  â TCC Bridge V2 Installation Complete!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo
echo "  Useful commands:"
echo "    pm2 list                     # See running processes"
echo "    pm2 logs tcc-bridge          # Live bridge logs"
echo "    pm2 logs cloudflared         # Live tunnel logs"
echo "    pm2 restart tcc-bridge       # Restart bridge"
echo "    pm2 restart cloudflared      # Restart tunnel"
echo "    pm2 save                     # Save process list for boot"
echo "    curl http://localhost:${BRIDGE_PORT}/health  # Health check"
echo
echo "  IMPORTANT: Make sure Termux:Boot app is installed from F-Droid"
echo "  so the bridge auto-starts when your phone reboots!"
echo
echo -e "${BLUE}  Bridge logs: $BRIDGE_DIR/logs/${NC}"
echo
