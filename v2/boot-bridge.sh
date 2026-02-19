#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
# Ensure cloudflared is in path or use full path
pm2 resurrect || pm2 start ~/ecosystem.config.js
# Health check push
python3 ~/state-push.py
