#!/data/data/com.termux/files/usr/bin/bash
# TCC Boot Script — Auto-start bridge + tunnel on phone reboot
# Place in ~/.termux/boot/tcc-boot.sh

sleep 5  # Wait for system to stabilize

# Start PM2 and resurrect saved processes
pm2 resurrect 2>/dev/null || {
    cd ~/tcc-bridge
    pm2 start ecosystem.config.js
}

# Ensure cloudflared is running
if ! pgrep cloudflared > /dev/null; then
    nohup cloudflared tunnel run --token "$(cat ~/.cf_token 2>/dev/null || echo '')" > /dev/null 2>&1 &
fi

# Log boot event
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") TCC boot complete" >> ~/tcc-boot.log
