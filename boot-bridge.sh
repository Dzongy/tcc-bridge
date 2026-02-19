#!/data/data/com.termux/files/usr/bin/bash
sleep 15
[ -f "$HOME/.bridge-env" ] && source "$HOME/.bridge-env"
cd "$HOME/tcc-bridge" && git pull origin main || true
pm2 resurrect || pm2 start ecosystem.config.js
crond 2>/dev/null || true