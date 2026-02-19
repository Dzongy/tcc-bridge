#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# setup-v2.sh â TCC Zenith Hive Bridge One-Tap Setup
# Commander: Run this once in Termux to bootstrap the full bridge stack.
# Usage: bash setup-v2.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# COLORS & LOGGING
# ---------------------------------------------------------------------------
RED='\033[0;31m';  GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m';     RESET='\033[0m'

log()  { echo -e "${CYAN}[TCC]${RESET} $*"; }
ok()   { echo -e "${GREEN}[OK]${RESET}  $*"; }
warn() { echo -e "${YELLOW}[WARN]${RESET} $*"; }
die()  { echo -e "${RED}[ERR]${RESET}  $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# BANNER
# ---------------------------------------------------------------------------
clear
echo -e "${BOLD}${CYAN}"
cat <<'BANNER'
 _______ ____  ____     ____       _     _
|__   __|  _ \/ ___|   |  _ \ _ __(_) __| | __ _  ___
   | |  | |_) \___ \   | |_) | '__| |/ _` |/ _` |/ _ \
   | |  |  __/ ___) |  |  _ <| |  | | (_| | (_| |  __/
   |_|  |_|   |____/   |_| \_\_|  |_|\__,_|\__, |\___|
                        Zenith Hive v2        |___/
BANNER
echo -e "${RESET}"
log "Commander, welcome. Starting TCC Bridge v2 setup..."
echo

# ---------------------------------------------------------------------------
# STEP 0 â Environment sanity check
# ---------------------------------------------------------------------------
if [[ -z "${TERMUX_VERSION:-}" && ! -d "/data/data/com.termux" ]]; then
    warn "This script is designed for Termux on Android."
    warn "Proceeding anyway â some steps may fail on non-Termux systems."
fi

HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
BIN_DIR="${PREFIX}/bin"
BRIDGE_DIR="${HOME_DIR}/tcc-bridge"
BOOT_DIR="${HOME_DIR}/.termux/boot"
ENV_FILE="${HOME_DIR}/.tcc_bridge_env"
CF_UUID="18ba1a49-fdf9-4a52-a27a-5250d397c5c5"
REPO_URL="https://github.com/Dzongy/tcc-bridge.git"

# ---------------------------------------------------------------------------
# STEP 1 â System package installation
# ---------------------------------------------------------------------------
log "Step 1/8 â Installing system packages via pkg..."
pkg update -y -q || warn "pkg update had warnings (continuing)"
pkg install -y python nodejs git termux-api wget curl openssh || die "pkg install failed"
ok "System packages installed."

# ---------------------------------------------------------------------------
# STEP 2 â Install cloudflared
# ---------------------------------------------------------------------------
log "Step 2/8 â Checking for cloudflared..."

if command -v cloudflared &>/dev/null; then
    ok "cloudflared already installed: $(cloudflared --version 2>&1 | head -1)"
else
    ARCH=$(uname -m)
    log "Detected architecture: ${ARCH}"

    case "${ARCH}" in
        aarch64|arm64)
            CF_ARCH="arm64" ;;
        armv7l|armv7)
            CF_ARCH="arm" ;;
        x86_64)
            CF_ARCH="amd64" ;;
        i686|i386)
            CF_ARCH="386" ;;
        *)
            die "Unsupported architecture for cloudflared: ${ARCH}" ;;
    esac

    CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}"
    log "Downloading cloudflared from: ${CF_URL}"
    wget -q --show-progress -O "${BIN_DIR}/cloudflared" "${CF_URL}" \
        || die "Failed to download cloudflared. Check your internet connection."
    chmod +x "${BIN_DIR}/cloudflared"
    ok "cloudflared installed: $(cloudflared --version 2>&1 | head -1)"
fi

# ---------------------------------------------------------------------------
# STEP 3 â Install Python dependencies
# ---------------------------------------------------------------------------
log "Step 3/8 â Installing Python packages..."
pip install --quiet --upgrade pip
pip install --quiet supabase httpx python-dotenv requests \
    || warn "Some pip packages failed â bridge_backup.py will use stdlib fallbacks."
ok "Python packages ready."

# ---------------------------------------------------------------------------
# STEP 4 â Install PM2 via npm
# ---------------------------------------------------------------------------
log "Step 4/8 â Installing PM2..."
if command -v pm2 &>/dev/null; then
    ok "PM2 already installed: $(pm2 --version)"
else
    npm install -g pm2 --loglevel=error || die "npm install pm2 failed."
    ok "PM2 installed: $(pm2 --version)"
fi

# ---------------------------------------------------------------------------
# STEP 5 â Clone or update tcc-bridge repository
# ---------------------------------------------------------------------------
log "Step 5/8 â Setting up tcc-bridge repository..."

if [[ -d "${BRIDGE_DIR}/.git" ]]; then
    log "Repository already exists â pulling latest changes..."
    git -C "${BRIDGE_DIR}" pull --rebase --autostash \
        && ok "Repository updated." \
        || warn "git pull had issues; using existing local version."
else
    log "Cloning ${REPO_URL} into ${BRIDGE_DIR}..."
    git clone "${REPO_URL}" "${BRIDGE_DIR}" || die "git clone failed. Check URL and connectivity."
    ok "Repository cloned."
fi

# Copy bridge_backup.py into the repo dir if not already there
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/bridge_backup.py" && ! -f "${BRIDGE_DIR}/bridge_backup.py" ]]; then
    cp "${SCRIPT_DIR}/bridge_backup.py" "${BRIDGE_DIR}/bridge_backup.py"
    ok "bridge_backup.py copied into ${BRIDGE_DIR}."
elif [[ -f "${BRIDGE_DIR}/bridge_backup.py" ]]; then
    ok "bridge_backup.py already present in ${BRIDGE_DIR}."
else
    warn "bridge_backup.py not found next to setup-v2.sh. Make sure to copy it manually to ${BRIDGE_DIR}."
fi

# ---------------------------------------------------------------------------
# STEP 6 â Environment variable setup (SUPABASE_URL / SUPABASE_KEY)
# ---------------------------------------------------------------------------
log "Step 6/8 â Configuring environment variables..."

# Source existing env file if present
[[ -f "${ENV_FILE}" ]] && source "${ENV_FILE}"

if [[ -z "${SUPABASE_URL:-}" ]]; then
    echo
    echo -e "${BOLD}Commander, please provide your Supabase credentials.${RESET}"
    echo -e "(These are stored in ${ENV_FILE} and exported on boot.)"
    read -r -p "  SUPABASE_URL  > " SUPABASE_URL
fi

if [[ -z "${SUPABASE_KEY:-}" ]]; then
    read -r -s -p "  SUPABASE_KEY  > " SUPABASE_KEY
    echo
fi

if [[ -z "${SUPABASE_URL}" || -z "${SUPABASE_KEY}" ]]; then
    warn "Supabase credentials not provided. bridge_backup.py will skip cloud push."
fi

# Write/update env file
cat > "${ENV_FILE}" <<EOF
# TCC Bridge environment â auto-generated by setup-v2.sh
export SUPABASE_URL="${SUPABASE_URL}"
export SUPABASE_KEY="${SUPABASE_KEY}"
export CF_TUNNEL_UUID="${CF_UUID}"
export NTFY_TOKEN="amos-bridge-2026"
export NTFY_TOPIC="tcc-zenith-hive"
export BRIDGE_DIR="${BRIDGE_DIR}"
EOF
chmod 600 "${ENV_FILE}"

# Source into current shell & add to .bashrc/.bash_profile if not already there
if ! grep -q "tcc_bridge_env" "${HOME_DIR}/.bashrc" 2>/dev/null; then
    echo "\n# TCC Bridge env\n[[ -f ${ENV_FILE} ]] && source ${ENV_FILE}" >> "${HOME_DIR}/.bashrc"
fi
source "${ENV_FILE}"
ok "Environment configured and persisted."

# ---------------------------------------------------------------------------
# STEP 7 â termux-boot persistence
# ---------------------------------------------------------------------------
log "Step 7/8 â Configuring termux-boot autostart..."

mkdir -p "${BOOT_DIR}"

cat > "${BOOT_DIR}/start-bridge.sh" <<BOOTSCRIPT
#!/data/data/com.termux/files/usr/bin/bash
# Auto-generated by setup-v2.sh â DO NOT EDIT MANUALLY
# Commander: This runs automatically on device boot via Termux:Boot.

sleep 8  # Give Android a moment to settle after boot

# Load environment
[[ -f "${ENV_FILE}" ]] && source "${ENV_FILE}"

# Start cloudflared tunnel
nohup cloudflared tunnel run ${CF_UUID} \
    >> "${HOME_DIR}/logs/cloudflared.log" 2>&1 &

# Resume PM2 processes
cd "${BRIDGE_DIR}"
pm2 resurrect || pm2 start ecosystem.config.js --env production
pm2 save

BOOTSCRIPT

chmod +x "${BOOT_DIR}/start-bridge.sh"
ok "Boot script written to ${BOOT_DIR}/start-bridge.sh"
warn "Commander: Make sure the Termux:Boot app is installed from F-Droid and has been opened at least once!"

# ---------------------------------------------------------------------------
# STEP 8 â Crontab for bridge_backup.py
# ---------------------------------------------------------------------------
log "Step 8/8 â Setting up cron job for bridge_backup.py..."

# Ensure crond is available
if ! command -v crond &>/dev/null; then
    pkg install -y cronie || warn "cronie install failed â cron won't run. Use Termux:Tasker as alternative."
fi

PYTHON_BIN="$(command -v python3 || command -v python)"
BACKUP_SCRIPT="${BRIDGE_DIR}/bridge_backup.py"
CRON_JOB="*/15 * * * * source ${ENV_FILE} && ${PYTHON_BIN} ${BACKUP_SCRIPT} >> ${HOME_DIR}/logs/bridge_backup.log 2>&1"

# Add cron entry only if not already present
( crontab -l 2>/dev/null | grep -qF "bridge_backup.py" ) \
    && warn "Cron entry already exists â skipping." \
    || ( ( crontab -l 2>/dev/null; echo "${CRON_JOB}" ) | crontab - && ok "Cron job added (every 15 min)." )

# Ensure logs directory exists
mkdir -p "${HOME_DIR}/logs"

# Start cron daemon if not running
if ! pgrep -x crond &>/dev/null; then
    crond -b 2>/dev/null || warn "crond failed to start â try 'crond' manually after setup."
    ok "crond started."
fi

# ---------------------------------------------------------------------------
# STEP 9 â Generate PM2 ecosystem file if missing
# ---------------------------------------------------------------------------
ECO_FILE="${BRIDGE_DIR}/ecosystem.config.js"

if [[ ! -f "${ECO_FILE}" ]]; then
    log "Generating default PM2 ecosystem.config.js..."
    cat > "${ECO_FILE}" <<ECOJS
// Auto-generated by setup-v2.sh
// Commander: Edit this file to add or modify bridge processes.
module.exports = {
  apps: [
    {
      name        : 'tcc-bridge',
      script      : 'bridge.py',
      interpreter : '${PYTHON_BIN}',
      cwd         : '${BRIDGE_DIR}',
      watch       : false,
      autorestart : true,
      env_production: {
        SUPABASE_URL : process.env.SUPABASE_URL,
        SUPABASE_KEY : process.env.SUPABASE_KEY,
        CF_TUNNEL_UUID: '${CF_UUID}',
        NTFY_TOKEN   : 'amos-bridge-2026',
        NTFY_TOPIC   : 'tcc-zenith-hive',
      },
    },
    {
      name        : 'cloudflared',
      script      : 'cloudflared',
      interpreter : 'none',
      args        : 'tunnel run ${CF_UUID}',
      watch       : false,
      autorestart : true,
      log_file    : '${HOME_DIR}/logs/cloudflared.log',
    },
  ],
};
ECOJS
    ok "ecosystem.config.js created."
else
    ok "ecosystem.config.js already exists â not overwriting."
fi

# ---------------------------------------------------------------------------
# LAUNCH PM2
# ---------------------------------------------------------------------------
log "Launching PM2 ecosystem..."
cd "${BRIDGE_DIR}"
pm2 start "${ECO_FILE}" --env production || warn "PM2 start had issues â check 'pm2 logs'."
pm2 save
ok "PM2 ecosystem started and saved."

# Run backup script once immediately to verify connectivity
log "Running initial bridge_backup.py health check..."
"${PYTHON_BIN}" "${BACKUP_SCRIPT}" && ok "Initial health snapshot pushed." || warn "Initial health check failed â check logs."

# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
echo
echo -e "${BOLD}${GREEN}ââââââââââââââââââââââââââââââââââââââââââââââââââââââââ${RESET}"
echo -e "${BOLD}${GREEN}â   TCC Zenith Hive Bridge v2 â Setup Complete! â      â${RESET}"
echo -e "${BOLD}${GREEN}ââââââââââââââââââââââââââââââââââââââââââââââââââââââââ${RESET}"
echo
echo -e "  ${CYAN}Bridge dir   :${RESET} ${BRIDGE_DIR}"
echo -e "  ${CYAN}PM2 status   :${RESET} pm2 list"
echo -e "  ${CYAN}Logs dir     :${RESET} ${HOME_DIR}/logs/"
echo -e "  ${CYAN}Boot script  :${RESET} ${BOOT_DIR}/start-bridge.sh"
echo -e "  ${CYAN}Env file     :${RESET} ${ENV_FILE}"
echo -e "  ${CYAN}CF Tunnel    :${RESET} ${CF_UUID}"
echo -e "  ${CYAN}ntfy topic   :${RESET} tcc-zenith-hive"
echo -e "  ${CYAN}Cron         :${RESET} bridge_backup.py every 15 min"
echo
echo -e "${YELLOW}Commander's checklist:${RESET}"
echo -e "  [ ] Termux:Boot app installed & opened at least once"
echo -e "  [ ] Termux:API app installed"
echo -e "  [ ] Cloudflare tunnel '${CF_UUID}' is active in your CF dashboard"
echo -e "  [ ] Run 'pm2 list' to verify processes are online"
echo -e "  [ ] Check '${HOME_DIR}/logs/' for any errors"
echo
echo -e "${BOLD}Bridge is live. The hive stands ready, Commander.${RESET}"
