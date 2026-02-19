#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge v7.0 — ONE-TAP PERMANENT SETUP
# God Builder: Kael

set -e
echo "🚀 Starting TCC Bridge Bulletproof Setup..."

# Step 1: Packages
pkg update -y
pkg install -y python python-pip git nodejs-lts termux-api cronie curl

# Step 2: PM2
npm install -g pm2

# Step 3: Clone/Update Repo
if [ ! -d "$HOME/tcc-bridge" ]; then
    git clone https://github.com/Dzongy/tcc-bridge.git "$HOME/tcc-bridge"
fi
cd "$HOME/tcc-bridge"
git pull origin main

# Step 4: Boot Script
mkdir -p "$HOME/.termux/boot"
cp boot-bridge.sh "$HOME/.termux/boot/boot-bridge.sh"
chmod +x "$HOME/.termux/boot/boot-bridge.sh"

# Step 5: PM2 Setup
pm2 start ecosystem.config.js
pm2 save
pm2 startup

echo "✅ Setup Complete! Bridge is now UNKILLABLE."
echo "Ensure Termux:Boot is installed and 'Acquire Wake Lock' is enabled."
