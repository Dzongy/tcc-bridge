
#!/data/data/com.termux/files/usr/bin/sh
# BRIDGE V2: ONE-TAP BULLETPROOF SETUP
echo "🚀 Starting Bridge V2 Sovereign Install..."

# 1. Update & Dependencies
pkg update -y
pkg install python nodejs-lts termux-api cloudflared -y
npm install -g pm2

# 2. Setup Directories
mkdir -p ~/.termux/boot
mkdir -p ~/tcc-bridge && cd ~/tcc-bridge

# 3. Download Files
REPO="https://raw.githubusercontent.com/Dzongy/tcc-bridge/main"
curl -sS -o bridge.py "$REPO/bridge.py"
curl -sS -o ecosystem.config.js "$REPO/ecosystem.config.js"
curl -sS -o state-push.py "$REPO/state-push.py"
curl -sS -o watchdog-v2.sh "$REPO/watchdog-v2.sh"
curl -sS -o ~/.termux/boot/boot-bridge.sh "$REPO/boot-bridge.sh"

chmod +x bridge.py state-push.py watchdog-v2.sh ~/.termux/boot/boot-bridge.sh

# 4. Start PM2
pm2 stop all || true
pm2 start ecosystem.config.js
pm2 save

echo "✅ BRIDGE V2 INSTALLED."
echo "Check ntfy tcc-zenith-hive for status."
