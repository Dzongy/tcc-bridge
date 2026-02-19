#!/data/data/com.termux/files/usr/bin/bash
set -e
pkg update -y
pkg install -y python nodejs termux-api coreutils lsof jq cloudflared
npm install -g pm2
mkdir -p $HOME/tcc/logs
mkdir -p $HOME/.termux/boot
REPO_RAW="https://raw.githubusercontent.com/Dzongy/tcc-bridge/main"
curl -sL $REPO_RAW/bridge.py -o $HOME/tcc/bridge.py
curl -sL $REPO_RAW/ecosystem.config.js -o $HOME/tcc/ecosystem.config.js
curl -sL $REPO_RAW/termux-boot.sh -o $HOME/.termux/boot/start-bridge.sh
chmod +x $HOME/.termux/boot/start-bridge.sh
cd $HOME/tcc
pm2 delete all || true
pm2 start ecosystem.config.js
pm2 save
pm2 startup
curl -d "Bridge V2: Bulletproof Install Complete" "https://ntfy.sh/tcc-zenith-hive"
