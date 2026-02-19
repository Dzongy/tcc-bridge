#!/data/data/com.termux/files/usr/bin/bash
# TCC BRIDGE V2 - ONE-TAP BULLETPROOF SETUP

echo "🚀 Launching TCC Bridge V2 Setup..."

# 1. System Update
echo "📦 Updating Termux environment..."
pkg update -y && pkg upgrade -y
pkg install -y python nodejs-lts git cloudflared termux-api termux-auth termux-boot

# 2. Global Tools
echo "⚙️ Installing PM2..."
npm install -g pm2

# 3. Directories
mkdir -p ~/tcc-bridge
mkdir -p ~/.termux/boot

# 4. Repo Sync
if [ -d "~/tcc-bridge/.git" ]; then
    cd ~/tcc-bridge && git pull
else
    git clone https://github.com/Dzongy/tcc-bridge ~/tcc-bridge
fi

# 5. Boot Integration
echo "🔌 Configuring auto-start..."
cat <<EOF > ~/.termux/boot/start-tcc.sh
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
sleep 15
pm2 resurrect
EOF
chmod +x ~/.termux/boot/start-tcc.sh

# 6. PM2 Startup (Termux Specific)
pm2 startup | tail -n 1 | bash

# 7. Deployment
cd ~/tcc-bridge
pm2 delete tcc-bridge cloudflared health-monitor 2>/dev/null
pm2 start ecosystem.config.js
pm2 save

echo "✅ BRIDGE V2 ONLINE"
echo "Public: https://zenith.cosmic-claw.com"
echo "Health: https://zenith.cosmic-claw.com/health"
