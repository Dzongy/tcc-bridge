#!/data/data/com.termux/files/usr/bin/bash
# TCC BRIDGE V2 - BULLETPROOF SETUP
# This script installs and configures everything for a permanent bridge.

echo "🚀 Starting TCC Bridge V2 Bulletproof Setup..."

# 1. Update Packages
echo "📦 Updating packages..."
pkg update -y && pkg upgrade -y
pkg install -y python nodejs-lts git cloudflared termux-api termux-auth termux-boot

# 2. Install PM2
echo "⚙️ Installing PM2..."
npm install -g pm2

# 3. Setup Directories
echo "📂 Setting up directories..."
mkdir -p ~/tcc-bridge
mkdir -p ~/.termux/boot

# 4. Clone or Update Repo
if [ -d "~/tcc-bridge/.git" ]; then
    echo "🔄 Updating repo..."
    cd ~/tcc-bridge && git pull
else
    echo "📥 Cloning repo..."
    git clone https://github.com/Dzongy/tcc-bridge ~/tcc-bridge
fi

# 5. Setup Termux:Boot Script
echo "🔌 Setting up boot script..."
cat <<EOF > ~/.termux/boot/start-tcc.sh
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
sleep 10
pm2 resurrect
EOF
chmod +x ~/.termux/boot/start-tcc.sh

# 6. Install Python Dependencies
echo "🐍 Installing python dependencies..."
pip install requests

# 7. Start with PM2
echo "🏎️ Starting Bridge with PM2..."
cd ~/tcc-bridge
pm2 delete tcc-bridge cloudflared state-pusher 2>/dev/null
pm2 start ecosystem.config.js
pm2 save

echo "✅ SETUP COMPLETE!"
echo "The bridge is now permanent and will survive reboots."
echo "Public URL: https://zenith.cosmic-claw.com"
echo "Health check: https://zenith.cosmic-claw.com/health"
