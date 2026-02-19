#!/data/data/com.termux/files/usr/bin/bash
echo "TCC BRIDGE V2 — BULLETPROOF INSTALLER"

# 1. Install Dependencies
pkg update -y && pkg upgrade -y
pkg install -y python nodejs termux-api curl git
npm install -g pm2

# 2. Setup Repo
if [ ! -d "$HOME/tcc-bridge" ]; then
  git clone https://github.com/Dzongy/tcc-bridge.git $HOME/tcc-bridge
else
  cd $HOME/tcc-bridge && git pull
fi

cd $HOME/tcc-bridge

# 3. Setup Termux:Boot
mkdir -p ~/.termux/boot
cp termux-boot.sh ~/.termux/boot/tcc-bridge
chmod +x ~/.termux/boot/tcc-bridge

# 4. Start PM2
pm2 start ecosystem.config.js
pm2 save

echo "INSTALLATION COMPLETE. Bridge is running via PM2."
echo "Ensure Termux:Boot app is installed and 'Keep alive' is on."
