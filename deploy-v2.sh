#!/data/data/com.termux/files/usr/bin/sh
echo "--- TCC BRIDGE V2 INSTALLER ---"
pkg update -y && pkg upgrade -y
pkg install -y python nodejs termux-api cloudflared

npm install -g pm2
pip install flask # In case we use flask later, but currently using http.server

cd ~
if [ ! -d "tcc-bridge" ]; then
  git clone https://github.com/Dzongy/tcc-bridge
fi
cd tcc-bridge
git pull origin main

# Setup Termux:Boot
mkdir -p ~/.termux/boot
cp boot-bridge.sh ~/.termux/boot/
chmod +x ~/.termux/boot/boot-bridge.sh

echo "Installation complete. Please edit ecosystem.config.js with your Cloudflare token, then run: pm2 start ecosystem.config.js"
