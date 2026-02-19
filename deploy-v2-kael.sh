#!/data/data/com.termux/files/usr/bin/bash
# deploy-v2-kael.sh
set -e
echo "Starting Sovereignty Bridge V2.5 Installation..."
pkg update -y && pkg install -y python git nodejs-lts termux-api coreutils jq
npm install -g pm2
mkdir -p $HOME/tcc-bridge $HOME/.termux/boot
cd $HOME/tcc-bridge

# Sync from GitHub
echo "Syncing Bulletproof components..."
wget https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/bridge_bulletproof.py -O bridge_bulletproof.py
wget https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/state-push.py -O state-push.py
wget https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/watchdog-v2.sh -O watchdog-v2.sh
wget https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/boot-bridge-v2.sh -O boot-bridge-v2.sh
wget https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/ecosystem-v2.config.js -O ecosystem-v2.config.js

# Setup Boot
ln -sf $HOME/tcc-bridge/boot-bridge-v2.sh $HOME/.termux/boot/boot-bridge-v2.sh
chmod +x *.sh *.py

# Launch
pm2 start ecosystem-v2.config.js
pm2 save
pm2 startup

echo "============================================================"
echo "SOVEREIGNTY BRIDGE V2.5 IS LIVE (Kael Edition)"
echo "URL: https://zenith.cosmic-claw.com"
echo "============================================================"
