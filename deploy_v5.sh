#!/data/data/com.termux/files/usr/bin/bash
# TCC BRIDGE V2 - ONE-TAP BULLETPROOF SETUP
set -e
echo "Starting TCC Bridge V2 Setup..."

pkg update -y && pkg upgrade -y
pkg install -y python nodejs cloudflared termux-api coreutils jq curl pm2

mkdir -p ~/tcc-bridge
cd ~/tcc-bridge

# Pull files from GitHub
BASE_URL="https://raw.githubusercontent.com/Dzongy/tcc-bridge/main"
curl -sO "$BASE_URL/bridge.py"
curl -sO "$BASE_URL/watchdog-v2.sh"
curl -sO "$BASE_URL/ecosystem.config.js"
curl -sO "$BASE_URL/state-push.py"

chmod +x *.sh *.py

# Setup Termux:Boot
mkdir -p ~/.termux/boot
cat <<EOF > ~/.termux/boot/boot-bridge.sh
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
cd ~/tcc-bridge
./watchdog-v2.sh &
pm2 resurrect || pm2 start ecosystem.config.js
EOF
chmod +x ~/.termux/boot/boot-bridge.sh

# Start everything
pm2 start ecosystem.config.js
pm2 save
./watchdog-v2.sh &

echo "Setup Complete. Bridge is LIVE."
curl -d "✅ Bridge V2 Setup Complete on Phone." "ntfy.sh/tcc-zenith-hive"
