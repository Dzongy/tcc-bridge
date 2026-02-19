#!/data/data/com.termux/files/usr/bin/bash
echo "--- BRIDGE V2 (v711) DEPLOYMENT STARTING ---"
pkg update -y && pkg upgrade -y
pkg install -y python nodejs-lts termux-api curl jq

# Install PM2
npm install -g pm2

# Setup files
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/bridge_v711.py -o bridge_v711.py
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/state_push_v711.py -o state_push_v711.py
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/ecosystem_v711.config.js -o ecosystem_v711.config.js
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/watchdog_v711.sh -o watchdog_v711.sh

chmod +x watchdog_v711.sh

# Ensure boot directory exists
mkdir -p ~/.termux/boot/
cat <<EOF > ~/.termux/boot/boot-bridge.sh
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
pm2 resurrect
pm2 start ~/ecosystem_v711.config.js
EOF
chmod +x ~/.termux/boot/boot-bridge.sh

# Start everything
pm2 start ecosystem_v711.config.js
pm2 save

echo "--- DEPLOYMENT v711 COMPLETE ---"
curl -d "Bridge v711 Live on $(hostname)" https://ntfy.sh/tcc-zenith-hive
