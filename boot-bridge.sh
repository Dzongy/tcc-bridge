#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge V2 — Boot Script
# Path: ~/.termux/boot/tcc-bridge

termux-wake-lock
cd $HOME/tcc-bridge

# 1. Start Cloudflared tunnel
# Note: UUID provided by user
cloudflared tunnel run --protocol http2 18ba1a49-fdf9-4a52-a27a-5250d397c5c5 &

# 2. Start PM2 ecosystem
# This starts bridge.py, watchdog.py, and state-push.py
pm2 start ecosystem.config.js
pm2 save

echo "BRIDGE V2 BOOT COMPLETE."
