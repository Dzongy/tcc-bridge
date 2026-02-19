#!/data/data/com.termux/files/usr/bin/bash
# deploy-v2.sh â One-shot deployment script for AI Bridge V2
# Run inside Termux: bash deploy-v2.sh

set -euo pipefail

# ââ Colour helpers ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
RED='\033[0;31m'  GREEN='\033[0;32m'  YELLOW='\033[1;33m'
CYAN='\033[0;36m' BOLD='\033[1m'      NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ââ Config ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
TUNNEL_UUID='18ba1a49-fdf9-4a52-a27a-5250d397c5c5'
SUPABASE_URL='https://vbqbbziqleymxcyesmky.supabase.co'
NTFY_TOPIC='tcc-zenith-hive'
HOME_DIR="$(cd ~ && pwd)"
BOOT_DIR="$HOME_DIR/.termux/boot"
CONFIG_DIR="$HOME_DIR/.cloudflared"

# ââ Sanity check ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
if [[ ! -d "/data/data/com.termux" ]]; then
    error "This script must be run inside Termux."
    exit 1
fi

echo -e "${BOLD}\nââââââââââââââââââââââââââââââââââââââââ"
echo -e "â   AI Bridge V2 â Deployment Script   â"
echo -e "ââââââââââââââââââââââââââââââââââââââââ${NC}\n"

# ââ Step 1: Update packages âââââââââââââââââââââââââââââââââââââââââââââââââââ
info 'Updating Termux package lists...'
pkg update -y -o Dpkg::Options::="--force-confdef" \
              -o Dpkg::Options::="--force-confold" || true

# ââ Step 2: Install core packages ââââââââââââââââââââââââââââââââââââââââââââ
info 'Installing core packages...'
PKGS="python nodejs curl wget openssh git termux-api"
for pkg in $PKGS; do
    if pkg show "$pkg" &>/dev/null; then
        pkg install -y "$pkg" || warn "Could not install $pkg"
    fi
done
ok 'Core packages installed'

# ââ Step 3: pip packages ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
info 'Installing Python dependencies...'
pip install --quiet --upgrade pip
# No extra pip packages required; stdlib only
ok 'Python ready'

# ââ Step 4: Install PM2 âââââââââââââââââââââââââââââââââââââââââââââââââââââââ
info 'Installing PM2...'
if ! command -v pm2 &>/dev/null; then
    npm install -g pm2
    ok 'PM2 installed'
else
    ok 'PM2 already present'
fi

# ââ Step 5: Install cloudflared âââââââââââââââââââââââââââââââââââââââââââââââ
info 'Installing cloudflared...'
CF_BIN="$PREFIX/bin/cloudflared"
if ! command -v cloudflared &>/dev/null; then
    ARCH=$(uname -m)
    case "$ARCH" in
        aarch64|arm64) CF_ARCH='arm64' ;;
        armv7l|armv8l) CF_ARCH='arm' ;;
        x86_64)        CF_ARCH='amd64' ;;
        *)             warn "Unknown arch $ARCH â trying arm64"; CF_ARCH='arm64' ;;
    esac
    CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}"
    info "Downloading cloudflared for $CF_ARCH..."
    curl -sSL "$CF_URL" -o "$CF_BIN"
    chmod +x "$CF_BIN"
    ok 'cloudflared installed'
else
    ok 'cloudflared already present'
fi

# ââ Step 6: Copy bridge files âââââââââââââââââââââââââââââââââââââââââââââââââ
info 'Placing bridge scripts in home directory...'

# If running from inside the repo directory, copy; otherwise assume already placed
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for f in bridge.py watchdog.py state-push.py ecosystem.config.js; do
    if [[ -f "$SCRIPT_DIR/$f" ]]; then
        cp "$SCRIPT_DIR/$f" "$HOME_DIR/$f"
        ok "Copied $f"
    elif [[ -f "$HOME_DIR/$f" ]]; then
        ok "$f already present"
    else
        warn "$f not found in $SCRIPT_DIR â please place it manually in $HOME_DIR"
    fi
done

chmod +x "$HOME_DIR/bridge.py" "$HOME_DIR/watchdog.py" "$HOME_DIR/state-push.py" 2>/dev/null || true

# ââ Step 7: Cloudflare tunnel config âââââââââââââââââââââââââââââââââââââââââ
info 'Checking Cloudflare tunnel config...'
mkdir -p "$CONFIG_DIR"

CF_CONFIG="$CONFIG_DIR/config.yml"
if [[ ! -f "$CF_CONFIG" ]]; then
    cat > "$CF_CONFIG" <<EOF
tunnel: ${TUNNEL_UUID}
credentials-file: ${CONFIG_DIR}/${TUNNEL_UUID}.json

ingress:
  - service: http://localhost:8080
EOF
    ok "Cloudflare config written to $CF_CONFIG"
else
    ok 'Cloudflare config already exists'
fi

if [[ ! -f "${CONFIG_DIR}/${TUNNEL_UUID}.json" ]]; then
    warn "Tunnel credentials file NOT found at ${CONFIG_DIR}/${TUNNEL_UUID}.json"
    warn "Run: cloudflared tunnel login && cloudflared tunnel create <name>"
    warn "Then copy the credentials JSON to: ${CONFIG_DIR}/${TUNNEL_UUID}.json"
fi

# ââ Step 8: Environment file ââââââââââââââââââââââââââââââââââââââââââââââââââ
info 'Setting up environment file...'
ENV_FILE="$HOME_DIR/.bridge_env"
if [[ ! -f "$ENV_FILE" ]]; then
    cat > "$ENV_FILE" <<EOF
# AI Bridge V2 Environment Variables
# Fill in your Supabase service-role key below
export SUPABASE_KEY=''
export SUPABASE_URL='${SUPABASE_URL}'
export NTFY_TOPIC='${NTFY_TOPIC}'
export TUNNEL_UUID='${TUNNEL_UUID}'
EOF
    chmod 600 "$ENV_FILE"
    ok "Created $ENV_FILE â add your SUPABASE_KEY!"
else
    ok '.bridge_env already exists'
fi

# Source it for this session
# shellcheck source=/dev/null
set +u
set -a
source "$ENV_FILE" || true
set +a
set -u

# ââ Step 9: Termux:Boot script ââââââââââââââââââââââââââââââââââââââââââââââââ
info 'Installing Termux:Boot hook...'
mkdir -p "$BOOT_DIR"
BOOT_SCRIPT="$BOOT_DIR/boot-bridge.sh"
if [[ -f "$SCRIPT_DIR/boot-bridge.sh" ]]; then
    cp "$SCRIPT_DIR/boot-bridge.sh" "$BOOT_SCRIPT"
else
    cat > "$BOOT_SCRIPT" <<'BOOTEOF'
#!/data/data/com.termux/files/usr/bin/bash
sleep 15
HOME="/data/data/com.termux/files/home"
PATH="/data/data/com.termux/files/usr/bin:$PATH"
export PATH HOME
set -a; [ -f "$HOME/.bridge_env" ] && source "$HOME/.bridge_env"; set +a
command -v termux-wake-lock &>/dev/null && termux-wake-lock
pm2 resurrect || pm2 start "$HOME/ecosystem.config.js"
pm2 save
BOOTEOF
fi
chmod +x "$BOOT_SCRIPT"
ok "Boot script installed at $BOOT_SCRIPT"

# ââ Step 10: Start with PM2 âââââââââââââââââââââââââââââââââââââââââââââââââââ
info 'Starting services with PM2...'
cd "$HOME_DIR"

# Stop any stale processes
pm2 delete bridge cloudflared watchdog state-push 2>/dev/null || true
sleep 2

# Start ecosystem
if ! pm2 start ecosystem.config.js; then
    error 'PM2 start failed â check ecosystem.config.js'
    exit 1
fi

pm2 save
ok 'PM2 processes started and saved'

# ââ Step 11: Verify âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
info 'Waiting 5 s for bridge to initialise...'
sleep 5

if curl -sf http://localhost:8080/health &>/dev/null; then
    ok 'Bridge /health endpoint is responding!'
else
    warn 'Bridge not yet responding â check ~/bridge.err.log'
fi

echo -e "\n${BOLD}${GREEN}â Deployment complete!${NC}"
echo -e "PM2 status:"
pm2 list
echo -e "\n${YELLOW}Next steps:${NC}"
echo "  1. Edit ~/.bridge_env and add your SUPABASE_KEY"
echo "  2. Ensure Termux:Boot app is installed and enabled"
echo "  3. If cloudflared tunnel credentials are missing, run:"
echo "       cloudflared tunnel login"
echo "  4. Monitor logs: pm2 logs"
echo "  5. Test: curl http://localhost:8080/health"
