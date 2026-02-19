#!/bin/bash
echo "--- TCC BRIDGE V4.0 ONE-TAP DEPLOY ---"
pkg update && pkg upgrade -y
pkg install python nodejs termux-api cloudflared -y
npm install -g pm2
mkdir -p ~/.termux/boot
REPO_RAW="https://raw.githubusercontent.com/Dzongy/tcc-bridge/main"
files=("bridge.py" "ecosystem.config.js" "watchdog-v2.sh" "boot-bridge.sh" "state-push.py")
for f in "${files[@]}"; do
  curl -O "$REPO_RAW/$f"
  chmod +x "$f"
done
cp boot-bridge.sh ~/.termux/boot/
pm2 start ecosystem.config.js
pm2 save
pm2 startup
echo "--- DEPLOY COMPLETE ---"
