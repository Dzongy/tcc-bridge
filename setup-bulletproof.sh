#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "--- TCC BRIDGE V2: BULLETPROOF SETUP ---"
pkg update -y
pkg install -y python nodejs termux-api coreutils lsof jq cloudflared
npm install -g pm2

# Wake lock
termux-wake-lock

# Clone/Update repo
cd $HOME
if [ -d "tcc-bridge" ]; then
  cd tcc-bridge && git pull
else
  git clone https://github.com/Dzongy/tcc-bridge.git
  cd tcc-bridge
fi

# Setup Termux Boot
mkdir -p ~/.termux/boot
echo "#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
pm2 resurrect" > ~/.termux/boot/tcc-bridge
chmod +x ~/.termux/boot/tcc-bridge

# PM2 Setup
pm2 start ecosystem.config.js
pm2 save
pm2 startup

echo "--- SETUP COMPLETE ---"
echo "Bridge is running. Monitor with 'pm2 list'"
