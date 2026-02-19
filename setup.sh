#!/data/data/com.termux/files/usr/bin/bash
set -e
pkg update -y && pkg upgrade -y
pkg install -y python nodejs-lts git curl openssh termux-api termux-services
npm install -g pm2
mkdir -p "$HOME/.termux/boot" "$HOME/.cloudflared"
[ -d "$HOME/tcc-bridge" ] || git clone https://github.com/Dzongy/tcc-bridge.git "$HOME/tcc-bridge"
cd "$HOME/tcc-bridge" && git pull origin main
cp boot-bridge.sh "$HOME/.termux/boot/boot-bridge.sh"
chmod +x "$HOME/.termux/boot/boot-bridge.sh" bridge.py supabase-backup.py
pm2 start ecosystem.config.js && pm2 save