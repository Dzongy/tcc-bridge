#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge — Termux Boot Script
# Path: ~/.termux/boot/boot-bridge.sh

sleep 15
export HOME="/data/data/com.termux/files/home"
cd $HOME/tcc-bridge

# Start Tunnel
cloudflared tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5 > $HOME/tunnel.log 2>&1 &

# Start PM2 Ecosystem
pm2 resurrect || pm2 start ecosystem.config.js
pm2 save

# Start system services
crond 2>/dev/null || true
