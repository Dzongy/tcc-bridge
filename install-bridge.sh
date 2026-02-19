#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# TCC Bridge V2 - One-Tap Installer
# Tunnel UUID: 18ba1a49-fdf9-4a52-a27a-5250d397c5c5
# Domain:      zenith.cosmic-claw.com
# ntfy topics: zenith-escape | tcc-zenith-hive
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
    echo '  âââââââââ âââââââ âââââââ'
    echo '     ââââââââââââââââââââââ'
    echo '     âââ   âââ     âââ'
    echo '     âââ   âââ     âââ'
    echo '     âââ   ââââââââââââââââ'
    echo '     âââ    âââââââ âââââââ'
    echo -e "  BRIDGE V2 - ONE-TAP INSTALLER${NC}"
    echo ''
}

step() { echo -e "${GREEN}[STEP]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERR ]${NC} $1"; exit 1; }

banner

TUNNEL_UUID='18ba1a49-fdf9-4a52-a27a-5250d397c5c5'
BRIDGE_DOMAIN='zenith.cosmic-claw.com'
NTFY_OPS='zenith-escape'
NTFY_HIVE='tcc-zenith-hive'
TCC_DIR="$HOME/tcc"
BIN_DIR="$HOME/bin"
BOOT_DIR="$HOME/.termux/boot"
CF_DIR="$HOME/.cloudflared"

# =============================================================================
# STEP 1: Update & Install Packages
# =============================================================================
step 'Updating package lists...'
pkg update -y -o Dpkg::Options::="--force-confnew" 2>/dev/null || warn 'pkg update had warnings'

step 'Installing required packages...'
pkg install -y python nodejs git curl wget openssl-tool termux-api termux-services 2>/dev/null || warn 'Some packages may have failed, continuing...'

# =============================================================================
# STEP 2: Create Directory Structure
# =============================================================================
step 'Creating TCC directory structure...'
mkdir -p "$TCC_DIR/logs" "$TCC_DIR/recordings" "$BIN_DIR" "$BOOT_DIR" "$CF_DIR"
export PATH="$BIN_DIR:/data/data/com.termux/files/usr/bin:$PATH"

# =============================================================================
# STEP 3: Install Python Dependencies
# =============================================================================
step 'Installing Python dependencies...'
pip install --upgrade pip --quiet 2>/dev/null || warn 'pip upgrade warning'
pip install psutil requests --quiet 2>/dev/null || warn 'psutil/requests install failed (non-critical)'
pip install openai-whisper --quiet 2>/dev/null || warn 'whisper install failed (STT will be limited)'

# =============================================================================
# STEP 4: Install PM2
# =============================================================================
step 'Installing PM2 globally...'
npm install -g pm2 2>/dev/null || err 'PM2 install failed. Check node installation.'
info "PM2 version: $(pm2 --version)"

# =============================================================================
# STEP 5: Install Cloudflared
# =============================================================================
step 'Installing cloudflared...'
ARCH=$(uname -m)
case $ARCH in
    aarch64) CF_ARCH='arm64' ;;
    armv7l)  CF_ARCH='arm'   ;;
    x86_64)  CF_ARCH='amd64' ;;
    *)       CF_ARCH='arm64'; warn "Unknown arch $ARCH, defaulting to arm64" ;;
esac
CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}"
info "Downloading cloudflared for ${CF_ARCH} from GitHub releases..."
wget -q --show-progress -O "$BIN_DIR/cloudflared" "$CF_URL" || err 'cloudflared download failed. Check internet connection.'
chmod +x "$BIN_DIR/cloudflared"
info "cloudflared version: $("$BIN_DIR/cloudflared" --version 2>/dev/null || echo 'binary installed')"

# =============================================================================
# STEP 6: Clone or Update tcc-bridge Repo
# =============================================================================
step 'Setting up tcc-bridge repository...'
if [ -d "$TCC_DIR/.git" ]; then
    info 'Repo already exists. Pulling latest changes...'
    git -C "$TCC_DIR" pull origin main 2>/dev/null || warn 'git pull failed, using existing files'
elif [ -d "$TCC_DIR" ] && [ "$(ls -A $TCC_DIR 2>/dev/null)" ]; then
    warn "$TCC_DIR exists but is not a git repo. Leaving existing files in place."
else
    info 'Attempting to clone tcc-bridge repo...'
    # Replace this URL with your actual repo if hosted remotely
    git clone https://github.com/your-org/tcc-bridge.git "$TCC_DIR" 2>/dev/null || {
        warn 'Clone failed (repo may be private or URL placeholder). Creating directory manually.'
        mkdir -p "$TCC_DIR"
    }
fi

# Copy scripts from current directory if available (manual install path)
[ -f bridge.py ]               && cp bridge.py               "$TCC_DIR/bridge.py"               && info 'bridge.py copied'
[ -f cloudflared_monitor.py ]  && cp cloudflared_monitor.py  "$TCC_DIR/cloudflared_monitor.py"  && info 'cloudflared_monitor.py copied'
[ -f ecosystem.config.js ]     && cp ecosystem.config.js     "$TCC_DIR/ecosystem.config.js"     && info 'ecosystem.config.js copied'
chmod +x "$TCC_DIR/bridge.py" "$TCC_DIR/cloudflared_monitor.py" 2>/dev/null || true

# =============================================================================
# STEP 7: Write ecosystem.config.js
# =============================================================================
step 'Writing ecosystem.config.js...'
if [ ! -f "$TCC_DIR/ecosystem.config.js" ]; then
    cat > "$TCC_DIR/ecosystem.config.js" << 'ECOEOF'
module.exports = {
  apps: [
    {
      name: 'tcc-bridge',
      script: 'python3',
      args: 'bridge.py',
      cwd: '/data/data/com.termux/files/home/tcc',
      autorestart: true,
      restart_delay: 5000,
      watch: false,
      max_memory_restart: '200M',
      env: {
        BRIDGE_PORT: '8080',
        NTFY_OPS_TOPIC: 'zenith-escape',
        NTFY_HIVE_TOPIC: 'tcc-zenith-hive',
        HEARTBEAT_INTERVAL: '30',
        PATH: '/data/data/com.termux/files/home/bin:/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/local/bin'
      },
      log_file: '/data/data/com.termux/files/home/tcc/logs/bridge-combined.log',
      out_file: '/data/data/com.termux/files/home/tcc/logs/bridge-out.log',
      error_file: '/data/data/com.termux/files/home/tcc/logs/bridge-err.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true
    },
    {
      name: 'tcc-tunnel',
      script: '/data/data/com.termux/files/home/bin/cloudflared',
      args: 'tunnel run --token 18ba1a49-fdf9-4a52-a27a-5250d397c5c5',
      autorestart: true,
      restart_delay: 5000,
      watch: false,
      max_memory_restart: '100M',
      env: {
        PATH: '/data/data/com.termux/files/home/bin:/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/local/bin',
        HOME: '/data/data/com.termux/files/home'
      },
      log_file: '/data/data/com.termux/files/home/tcc/logs/tunnel-combined.log',
      out_file: '/data/data/com.termux/files/home/tcc/logs/tunnel-out.log',
      error_file: '/data/data/com.termux/files/home/tcc/logs/tunnel-err.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true
    },
    {
      name: 'tcc-monitor',
      script: 'python3',
      args: 'cloudflared_monitor.py',
      cwd: '/data/data/com.termux/files/home/tcc',
      autorestart: true,
      restart_delay: 5000,
      watch: false,
      max_memory_restart: '100M',
      env: {
        TUNNEL_UUID: '18ba1a49-fdf9-4a52-a27a-5250d397c5c5',
        NTFY_OPS_TOPIC: 'zenith-escape',
        PATH: '/data/data/com.termux/files/home/bin:/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/local/bin'
      },
      log_file: '/data/data/com.termux/files/home/tcc/logs/monitor-combined.log',
      out_file: '/data/data/com.termux/files/home/tcc/logs/monitor-out.log',
      error_file: '/data/data/com.termux/files/home/tcc/logs/monitor-err.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true
    }
  ]
};
ECOEOF
    info 'ecosystem.config.js written.'
else
    info 'ecosystem.config.js already exists, skipping write.'
fi

# =============================================================================
# STEP 8: Write .env File
# =============================================================================
step 'Creating environment config...'
if [ ! -f "$TCC_DIR/.env" ]; then
    cat > "$TCC_DIR/.env" << ENVEOF
# TCC Bridge Environment Variables
# !! EDIT THESE BEFORE STARTING !!
BRIDGE_AUTH=your_secret_token_here
SUPABASE_URL=https://vbqbbziqleymxcyesmky.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
NTFY_OPS_TOPIC=zenith-escape
NTFY_HIVE_TOPIC=tcc-zenith-hive
BRIDGE_PORT=8080
HEARTBEAT_INTERVAL=30
TUNNEL_UUID=18ba1a49-fdf9-4a52-a27a-5250d397c5c5
ENVEOF
    warn '.env created at ~/tcc/.env - EDIT IT with your real credentials before starting!'
else
    info '.env already exists, skipping.'
fi

# =============================================================================
# STEP 9: Configure Cloudflare Tunnel (cert/config path)
# =============================================================================
step 'Configuring Cloudflare tunnel config...'
if [ ! -f "$CF_DIR/config.yml" ]; then
    cat > "$CF_DIR/config.yml" << CFEOF
tunnel: 18ba1a49-fdf9-4a52-a27a-5250d397c5c5
credentials-file: /data/data/com.termux/files/home/.cloudflared/18ba1a49-fdf9-4a52-a27a-5250d397c5c5.json

ingress:
  - hostname: zenith.cosmic-claw.com
    service: http://localhost:8080
  - service: http_status:404
CFEOF
    info 'Cloudflare tunnel config written to ~/.cloudflared/config.yml'
    warn 'You must place your tunnel credentials JSON at:'
    warn "  ~/.cloudflared/18ba1a49-fdf9-4a52-a27a-5250d397c5c5.json"
    warn 'Or use: cloudflared tunnel login  (then re-run this installer)'
else
    info 'Cloudflare tunnel config already exists, skipping.'
fi

# =============================================================================
# STEP 10: Install termux-boot.sh
# =============================================================================
step 'Installing Termux boot script...'
if [ -f termux-boot.sh ]; then
    cp termux-boot.sh "$BOOT_DIR/termux-boot.sh"
    chmod +x "$BOOT_DIR/termux-boot.sh"
    info 'termux-boot.sh installed to ~/.termux/boot/'
else
    cat > "$BOOT_DIR/termux-boot.sh" << 'BOOTEOF'
#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge V2 - Termux Boot Script
export PATH="/data/data/com.termux/files/home/bin:/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/local/bin:$PATH"
export HOME="/data/data/com.termux/files/home"
sleep 15
if [ -f "$HOME/tcc/.env" ]; then
    set -a
    source "$HOME/tcc/.env"
    set +a
fi
pm2 resurrect 2>/dev/null || pm2 start "$HOME/tcc/ecosystem.config.js"
pm2 save
BOOTEOF
    chmod +x "$BOOT_DIR/termux-boot.sh"
    info 'termux-boot.sh generated and installed to ~/.termux/boot/'
fi

# =============================================================================
# STEP 11: Load .env and Start PM2
# =============================================================================
step 'Loading environment variables...'
if [ -f "$TCC_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$TCC_DIR/.env" 2>/dev/null || true
    set +a
fi

if [ "$BRIDGE_AUTH" = 'your_secret_token_here' ] || [ -z "$BRIDGE_AUTH" ]; then
    warn 'BRIDGE_AUTH is still a placeholder. Bridge will start but is UNAUTHENTICATED.'
    warn 'Edit ~/tcc/.env then run: pm2 restart tcc-bridge'
fi

step 'Starting PM2 ecosystem...'
cd "$TCC_DIR"
pm2 delete all 2>/dev/null || true
pm2 start ecosystem.config.js || warn 'PM2 start had issues. Run: pm2 logs'
pm2 save || warn 'pm2 save failed'

# =============================================================================
# STEP 12: Configure PM2 Startup for Termux
# =============================================================================
step 'Configuring PM2 for auto-start on boot...'
pm2 startup 2>/dev/null || warn 'pm2 startup had warnings (normal in Termux - boot script handles this)'
info 'Boot persistence handled by ~/.termux/boot/termux-boot.sh'

# =============================================================================
# STEP 13: Wait and Print Status
# =============================================================================
step 'Waiting for processes to stabilise...'
sleep 5

echo ''
echo -e "${GREEN}${BOLD}ââââââââââââââââââââââââââââââââââââââââââââââââââââ${NC}"
echo -e "${GREEN}${BOLD}   â  TCC BRIDGE V2 INSTALLATION COMPLETE!${NC}"
echo -e "${GREEN}${BOLD}ââââââââââââââââââââââââââââââââââââââââââââââââââââ${NC}"
echo ''
echo -e "${CYAN}${BOLD}ð Public Endpoint:${NC}"
echo "   https://zenith.cosmic-claw.com/health"
echo ''
echo -e "${CYAN}${BOLD}ð ntfy Topics:${NC}"
echo "   Ops alerts : https://ntfy.sh/zenith-escape"
echo "   Hive events: https://ntfy.sh/tcc-zenith-hive"
echo ''
echo -e "${CYAN}${BOLD}ð°  Tunnel UUID:${NC}"
echo "   18ba1a49-fdf9-4a52-a27a-5250d397c5c5"
echo ''
echo -e "${CYAN}${BOLD}ð Process Status:${NC}"
pm2 list 2>/dev/null || true
echo ''
echo -e "${CYAN}${BOLD}âï¸  Useful Commands:${NC}"
echo '  pm2 status              - See all process states'
echo '  pm2 logs tcc-bridge     - Live bridge logs'
echo '  pm2 logs tcc-tunnel     - Live tunnel logs'
echo '  pm2 logs tcc-monitor    - Live monitor logs'
echo '  pm2 restart all         - Restart everything'
echo '  pm2 stop all            - Stop everything'
echo ''
echo -e "${CYAN}${BOLD}ð©º Quick Health Checks:${NC}"
echo '  curl http://localhost:8080/health'
echo '  curl https://zenith.cosmic-claw.com/health'
echo ''
echo -e "${YELLOW}${BOLD}â ï¸  IMPORTANT:${NC}"
echo '  1. Edit ~/tcc/.env with your real BRIDGE_AUTH and SUPABASE_KEY'
echo '  2. Place your Cloudflare credentials JSON at:'
echo '     ~/.cloudflared/18ba1a49-fdf9-4a52-a27a-5250d397c5c5.json'
echo '  3. After editing .env, run: pm2 restart all'
echo '  4. Install Termux:Boot from F-Droid for auto-start on phone reboot'
echo ''
echo -e "${GREEN}${BOLD}ââââââââââââââââââââââââââââââââââââââââââââââââââââ${NC}"
