#!/data/data/com.termux/files/usr/bin/sh
# TCC Bridge V2 Bulletproof Installer
echo "Starting TCC Bridge V2 Deployment..."

# 1. Update packages
pkg update -y && pkg upgrade -y
pkg install -y python nodejs git termux-api termux-auth

# 2. Setup Node environment
npm install -g pm2

# 3. Clone or Update Repo
if [ -d "$HOME/tcc-bridge" ]; then
    cd $HOME/tcc-bridge && git pull
else
    git clone https://github.com/Dzongy/tcc-bridge.git $HOME/tcc-bridge
    cd $HOME/tcc-bridge
fi

# 4. Setup Termux:Boot
mkdir -p $HOME/.termux/boot
cat <<EOF > $HOME/.termux/boot/start-bridge
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
cd $HOME/tcc-bridge
pm2 start ecosystem.config.js
pm2 save
EOF
chmod +x $HOME/.termux/boot/start-bridge

# 5. Start everything
pm2 start ecosystem.config.js
pm2 save

echo "Deployment complete. Bridge is running under PM2."
echo "Check status with: pm2 status"
