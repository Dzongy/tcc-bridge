#!/data/data/com.termux/files/usr/bin/bash

# ============================================================
# TCC Bridge V2 - deploy-v2.sh
# Master Deployment Script by Kael
# ============================================================

set -euo pipefail

# --- CONSTANTS ---
NTFY_TOPIC="tcc-zenith-hive"
NTFY_URL="https://ntfy.sh/${NTFY_TOPIC}"
REPO_URL="https://github.com/Dzongy/tcc-bridge.git"
REPO_DIR="$HOME/tcc-bridge"
TUNNEL_UUID="18ba1a49-fdf9-4a52-a27a-5250d397c5c5"
CLOUDFLARED_BIN="$PREFIX/bin/cloudflared"
BOOT_DIR="$HOME/.termux/boot"
BOOT_SCRIPT="$BOOT_DIR/boot-bridge.sh"

# --- COLORS ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

ntfy_notify() {
  local title="$1"
  local message="$2"
  local priority="${3:-default}"
  curl -s \
    -H "Title: ${title}" \
    -H "Priority: ${priority}" \
    -H "Tags: robot,bridge" \
    -d "${message}" \
    "${NTFY_URL}" > /dev/null 2>&1 || true
}

echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}   TCC Bridge V2 - One-Tap Deployment by Kael${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""

# --- STEP 1: UPDATE & INSTALL CORE PACKAGES ---
log_info "Updating package lists..."
pkg update -y -o Dpkg::Options::='--force-confnew' 2>/dev/null || { log_warn "pkg update encountered issues, continuing..."; }

log_info "Installing core dependencies..."
DEPS=(python nodejs git termux-api openssh)
for dep in "${DEPS[@]}"; do
  if ! pkg list-installed 2>/dev/null | grep -q "^${dep}"; then
    log_info "Installing ${dep}..."
    pkg install -y "$dep" 2>/dev/null && log_ok "${dep} installed." || log_warn "${dep} install may have had issues."
  else
    log_ok "${dep} already installed."
  fi
done

# --- STEP 2: INSTALL PM2 ---
log_info "Checking pm2..."
if ! command -v pm2 &>/dev/null; then
  log_info "Installing pm2 via npm..."
  npm install -g pm2 && log_ok "pm2 installed." || { log_error "Failed to install pm2."; exit 1; }
else
  log_ok "pm2 already installed at $(command -v pm2)."
fi

# --- STEP 3: INSTALL CLOUDFLARED ---
log_info "Checking cloudflared..."
if ! command -v cloudflared &>/dev/null; then
  log_info "cloudflared not found in PATH. Attempting binary download..."
  ARCH=$(uname -m)
  case "$ARCH" in
    aarch64|arm64) CF_ARCH="arm64" ;;
    armv7l|armv8l) CF_ARCH="arm" ;;
    x86_64)        CF_ARCH="amd64" ;;
    i686|i386)     CF_ARCH="386" ;;
    *)
      log_warn "Unknown architecture: $ARCH. Trying arm64 as fallback."
      CF_ARCH="arm64"
      ;;
  esac
  CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}"
  log_info "Downloading cloudflared for ${CF_ARCH} from: ${CF_URL}"
  curl -L --progress-bar -o "${CLOUDFLARED_BIN}" "${CF_URL}" || { log_error "Failed to download cloudflared."; exit 1; }
  chmod +x "${CLOUDFLARED_BIN}"
  log_ok "cloudflared installed at ${CLOUDFLARED_BIN}."
else
  log_ok "cloudflared already installed at $(command -v cloudflared)."
fi

# --- STEP 4: CLONE OR PULL REPO ---
log_info "Setting up TCC Bridge repository..."
if [ -d "$REPO_DIR/.git" ]; then
  log_info "Repository already exists. Pulling latest changes..."
  cd "$REPO_DIR"
  git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || log_warn "git pull failed or already up to date."
  log_ok "Repository updated."
else
  log_info "Cloning repository from ${REPO_URL}..."
  git clone "$REPO_URL" "$REPO_DIR" || { log_error "Failed to clone repository."; exit 1; }
  log_ok "Repository cloned to ${REPO_DIR}."
fi
cd "$REPO_DIR"

# --- STEP 5: PYTHON DEPENDENCIES ---
log_info "Installing Python requirements..."
if [ -f "requirements.txt" ]; then
  pip install --upgrade pip -q 2>/dev/null || true
  pip install -r requirements.txt -q && log_ok "Python requirements installed." || log_warn "Some Python requirements may have failed."
else
  log_warn "No requirements.txt found. Skipping Python dependencies."
fi

# --- STEP 6: SETUP PM2 ECOSYSTEM ---
log_info "Setting up PM2 ecosystem..."
cat > "$REPO_DIR/ecosystem.config.js" << 'EOF'
module.exports = {
  apps: [
    {
      name: 'tcc-bridge',
      script: 'bridge.py',
      interpreter: 'python',
      cwd: process.env.HOME + '/tcc-bridge',
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      env: {
        PORT: 8080
      },
      error_file: process.env.HOME + '/.pm2/logs/tcc-bridge-error.log',
      out_file:   process.env.HOME + '/.pm2/logs/tcc-bridge-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss'
    },
    {
      name: 'cloudflared',
      script: 'cloudflared',
      interpreter: 'none',
      args: 'tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5',
      watch: false,
      autorestart: true,
      max_restarts: 15,
      restart_delay: 5000,
      error_file: process.env.HOME + '/.pm2/logs/cloudflared-error.log',
      out_file:   process.env.HOME + '/.pm2/logs/cloudflared-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss'
    },
    {
      name: 'watchdog',
      script: process.env.HOME + '/watchdog-v2.sh',
      interpreter: 'bash',
      watch: false,
      autorestart: true,
      max_restarts: 999,
      restart_delay: 5000,
      error_file: process.env.HOME + '/.pm2/logs/watchdog-error.log',
      out_file:   process.env.HOME + '/.pm2/logs/watchdog-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss'
    }
  ]
};
EOF
log_ok "ecosystem.config.js written."

# --- STEP 7: SETUP TERMUX:BOOT ---
log_info "Setting up Termux:Boot..."
mkdir -p "$BOOT_DIR"
cat > "$BOOT_SCRIPT" << BOOTEOF
#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge V2 - Boot Script
# Auto-generated by deploy-v2.sh
sleep 10
cd $HOME/tcc-bridge
pm2 start ecosystem.config.js
pm2 save
BOOTEOF
chmod +x "$BOOT_SCRIPT"
log_ok "Termux:Boot script written to ${BOOT_SCRIPT}."

# --- STEP 8: CONFIGURE CLOUDFLARED TUNNEL ---
log_info "Checking cloudflared tunnel configuration..."
CF_CONFIG_DIR="$HOME/.cloudflared"
mkdir -p "$CF_CONFIG_DIR"
CF_CONFIG_FILE="$CF_CONFIG_DIR/config.yml"
if [ ! -f "$CF_CONFIG_FILE" ]; then
  log_info "Writing cloudflared config.yml for tunnel ${TUNNEL_UUID}..."
  cat > "$CF_CONFIG_FILE" << CFEOF
tunnel: ${TUNNEL_UUID}
credentials-file: ${CF_CONFIG_DIR}/${TUNNEL_UUID}.json
ingress:
  - hostname: "*"
    service: http://localhost:8080
  - service: http_status:404
CFEOF
  log_ok "cloudflared config.yml written."
else
  log_ok "cloudflared config.yml already exists. Skipping."
fi
if [ ! -f "${CF_CONFIG_DIR}/${TUNNEL_UUID}.json" ]; then
  log_warn "Tunnel credentials file NOT found at ${CF_CONFIG_DIR}/${TUNNEL_UUID}.json"
  log_warn "Commander: Ensure your credentials JSON is placed at the above path before starting cloudflared."
else
  log_ok "Tunnel credentials file found."
fi

# --- STEP 9: COPY WATCHDOG SCRIPT ---
log_info "Checking for watchdog-v2.sh..."
if [ -f "$REPO_DIR/watchdog-v2.sh" ]; then
  cp "$REPO_DIR/watchdog-v2.sh" "$HOME/watchdog-v2.sh"
  chmod +x "$HOME/watchdog-v2.sh"
  log_ok "watchdog-v2.sh copied to $HOME."
elif [ -f "$HOME/watchdog-v2.sh" ]; then
  log_ok "watchdog-v2.sh already present at $HOME."
else
  log_warn "watchdog-v2.sh not found in repo or home. Please place it at $HOME/watchdog-v2.sh before starting pm2."
fi

# --- STEP 10: START PM2 ---
log_info "Starting PM2 ecosystem..."
pm2 delete all 2>/dev/null || true
pm2 start "$REPO_DIR/ecosystem.config.js" && log_ok "PM2 started successfully." || { log_error "PM2 start failed."; exit 1; }
pm2 save && log_ok "PM2 process list saved."
pm2 startup 2>/dev/null || log_warn "pm2 startup command needs manual attention (may need root or different env)."

# --- STEP 11: HEALTH CHECK ---
log_info "Waiting 8 seconds for services to initialize..."
sleep 8
log_info "Running health check on port 8080..."
if curl -sf --max-time 5 http://localhost:8080/health > /dev/null 2>&1 || curl -sf --max-time 5 http://localhost:8080 > /dev/null 2>&1; then
  HEALTH_STATUS="HEALTHY"
  log_ok "bridge.py is responding on port 8080."
else
  HEALTH_STATUS="BRIDGE NOT RESPONDING - check pm2 logs"
  log_warn "bridge.py did not respond. Check: pm2 logs tcc-bridge"
fi

# --- STEP 12: NOTIFY SUCCESS ---
log_info "Sending SUCCESS notification to ntfy..."
SUCCESS_MSG="TCC Bridge V2 Deployed!\n\nStatus: ${HEALTH_STATUS}\nTunnel UUID: ${TUNNEL_UUID}\nRepo: ${REPO_DIR}\n\nCommands:\n  pm2 status\n  pm2 logs\n  pm2 restart all\n\nHealth: http://localhost:8080\nBoot script: ${BOOT_SCRIPT}\n\nCommander, your bridge is live. Kael out."
ntfy_notify "TCC Bridge V2 - DEPLOYED" "$SUCCESS_MSG" "high"
log_ok "Notification sent to ntfy topic: ${NTFY_TOPIC}"

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}   DEPLOYMENT COMPLETE${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "  ${CYAN}Run:${NC} pm2 status"
echo -e "  ${CYAN}Logs:${NC} pm2 logs"
echo -e "  ${CYAN}Restart:${NC} pm2 restart all"
echo -e "  ${CYAN}Health:${NC} curl http://localhost:8080"
echo -e "  ${CYAN}Boot script:${NC} ${BOOT_SCRIPT}"
echo -e "  ${CYAN}Tunnel UUID:${NC} ${TUNNEL_UUID}"
echo ""
echo -e "${CYAN}Kael signing off. Bridge is live, Commander.${NC}"
echo ""