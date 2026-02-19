#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# TCC Bridge v5.1 - ONE-TAP BULLETPROOF SETUP
# ============================================================
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  [OK]${NC} $*"; }
warn() { echo -e "${YELLOW}  [!!]${NC} $*"; }
err()  { echo -e "${RED}  [ERR]${NC} $*"; }

echo "Starting Sovereignty Bridge V2 Installation..."

# 1. Update & Install Dependencies
pkg update -y && pkg upgrade -y
pkg install -y python git nodejs-lts termux-api coreutils jq nmap-ncat
ok "System packages installed."

# 2. PM2 & Cloudflared
npm install -g pm2
if ! command -v cloudflared &> /dev/null; then
  wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O $PREFIX/bin/cloudflared
  chmod +x $PREFIX/bin/cloudflared
fi
ok "PM2 and Cloudflared ready."

# 3. Setup Directories
mkdir -p $HOME/tcc-bridge
mkdir -p $HOME/.termux/boot
cd $HOME/tcc-bridge

# 4. Auth & Env
echo "BRIDGE_AUTH=amos-bridge-2026" > .bridge-env
echo "BRIDGE_PORT=8765" >> .bridge-env

# 5. Boot Script
cat <<EOF > $HOME/.termux/boot/boot-bridge.sh
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
sleep 15
pm2 resurrect || pm2 start $HOME/tcc-bridge/ecosystem.config.js
EOF
chmod +x $HOME/.termux/boot/boot-bridge.sh
ok "Termux:Boot script configured."

# 6. Launch
pm2 start ecosystem.config.js
pm2 save
pm2 startup

ok "BRIDGE V2 IS LIVE."
echo "URL: https://zenith.cosmic-claw.com"
