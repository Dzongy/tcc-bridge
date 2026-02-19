#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# TCC Bridge - One-Tap Installer
# Run this once. It handles everything.
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

banner() {
    echo -e "${CYAN}"
    echo '  ████████╗ ██████╗ ██████╗'
    echo '     ██╔══╝██╔════╝██╔════╝'
    echo '     ██║   ██║     ██║'
    echo '     ██║   ██║     ██║'
    echo '     ██║   ╚██████╗╚██████╗'
    echo '     ╚═╝    ╚═════╝ ╚═════╝'
    echo -e "  BRIDGE V2 - ONE-TAP INSTALLER${NC}"
    echo ''
}

step() { echo -e "${GREEN}[STEP]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERR ]${NC} $1"; exit 1; }

banner

# --- 1. Update & Install Packages ---
step 'Updating package lists...'
pkg update -y -o Dpkg::Options::="--force-confnew" 2>/dev/null || warn 'pkg update had warnings'

step 'Installing required packages...'
pkg install -y python nodejs termux-api curl wget openssl-tool 2>/dev/null || warn 'Some packages may have failed'

# --- 2. Install Python deps ---
step 'Installing Python dependencies...'
pip install --upgrade pip --quiet
pip install psutil --quiet || warn 'psutil install failed (non-critical)'
pip install openai-whisper --quiet || warn 'whisper install failed (STT will be limited)'

# --- 3. Install Node/PM2 ---
step 'Installing PM2...'
npm install -g pm2 2>/dev/null || err 'PM2 install failed. Check node.'
info "PM2 version: $(pm2 --version)"

# --- 4. Install Cloudflared ---
step 'Installing cloudflared...'
ARCH=$(uname -m)
case $ARCH in
    aarch64) CF_ARCH='arm64' ;;
    armv7l)  CF_ARCH='arm' ;;
    x86_64)  CF_ARCH='amd64' ;;
    *)       CF_ARCH='arm64'; warn "Unknown arch $ARCH, defaulting to arm64" ;;
esac
CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}"
info "Downloading cloudflared for ${CF_ARCH}..."
wget -q --show-progress -O ~/bin/cloudflared "$CF_URL" || err 'cloudflared download failed'
chmod +x ~/bin/cloudflared
mkdir -p ~/bin
export PATH="$HOME/bin:$PATH"
info "cloudflared version: $(cloudflared --version 2>/dev/null || echo 'installed')"

# --- 5. Create TCC Directory Structure ---
step 'Creating TCC directory structure...'
mkdir -p ~/tcc/logs ~/tcc/recordings

# --- 6. Write env file ---
step 'Creating environment config...'
if [ ! -f ~/tcc/.env ]; then
    echo -e "${YELLOW}You will need to set these in ~/tcc/.env after install:${NC}"
    cat > ~/tcc/.env << 'ENVEOF'
# TCC Bridge Environment Variables
# Fill these in before starting!
BRIDGE_AUTH=your_secret_token_here
SUPABASE_URL=https://vbqbbziqleymxcyesmky.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
NTFY_OPS_TOPIC=zenith-escape
NTFY_HIVE_TOPIC=tcc-zenith-hive
BRIDGE_PORT=8080
HEARTBEAT_INTERVAL=30
ENVEOF
    info '.env created at ~/tcc/.env - EDIT IT before starting!'
else
    info '.env already exists, skipping.'
fi

# --- 7. Copy scripts (they should be in current dir) ---
step 'Copying scripts to ~/tcc/...'
[ -f bridge.py ] && cp bridge.py ~/tcc/bridge.py && info 'bridge.py installed' || warn 'bridge.py not found in current dir'
[ -f cloudflared_monitor.py ] && cp cloudflared_monitor.py ~/tcc/cloudflared_monitor.py && info 'cloudflared_monitor.py installed' || warn 'cloudflared_monitor.py not found'
[ -f ecosystem.config.js ] && cp ecosystem.config.js ~/tcc/ecosystem.config.js && info 'ecosystem.config.js installed' || warn 'ecosystem.config.js not found'

chmod +x ~/tcc/bridge.py ~/tcc/cloudflared_monitor.py 2>/dev/null || true

# --- 8. Load env and start PM2 ---
step 'Loading environment variables...'
if [ -f ~/tcc/.env ]; then
    export $(grep -v '^#' ~/tcc/.env | grep -v '^$' | xargs) 2>/dev/null || true
fi

# Check if auth is still placeholder
if [ "$BRIDGE_AUTH" = 'your_secret_token_here' ] || [ -z "$BRIDGE_AUTH" ]; then
    warn 'BRIDGE_AUTH is not set or is placeholder. Bridge will run UNAUTHENTICATED.'
    warn 'Edit ~/tcc/.env and restart.'
fi

step 'Starting PM2 ecosystem...'
cd ~/tcc
pm2 start ecosystem.config.js || warn 'PM2 start had issues. Check: pm2 logs'
pm2 save || warn 'pm2 save failed'

# --- 9. Setup pm2 startup (Termux) ---
step 'Configuring PM2 for Termux boot...'
pmixup_info=$(pm2 startup 2>/dev/null || true)
info 'PM2 startup configured.'

# --- 10. Final Report ---
echo ''
echo -e "${GREEN}${BOLD}================================================${NC}"
echo -e "${GREEN}${BOLD}  TCC BRIDGE V2 INSTALLATION COMPLETE!${NC}"
echo -e "${GREEN}${BOLD}================================================${NC}"
echo ''
echo -e "${CYAN}Status Commands:${NC}"
echo '  pm2 status          - See all processes'
echo '  pm2 logs tcc-bridge - Live bridge logs'
echo '  pm2 logs tcc-tunnel - Live tunnel logs'
echo '  pm2 logs tcc-monitor- Live monitor logs'
echo ''
echo -e "${CYAN}Quick Health Check:${NC}"
echo '  curl http://localhost:8080/health'
echo '  curl https://zenith.cosmic-claw.com/health'
echo ''
echo -e "${YELLOW}IMPORTANT: Edit ~/tcc/.env with your credentials!${NC}"
echo ''
