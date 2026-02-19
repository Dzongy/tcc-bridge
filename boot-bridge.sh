#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge — Termux Boot Script
# Path: ~/.termux/boot/boot-bridge.sh

sleep 15
export HOME="/data/data/com.termux/files/home"
export PATH="$PATH:$HOME/bin"

[ -f "$HOME/.bridge-env" ] && source "$HOME/.bridge-env"

cd "$HOME/tcc-bridge" || exit 1

# Auto-update on boot
git pull origin main || true

# Resurrection
pm2 resurrect || pm2 start ecosystem.config.js
pm2 save

# Start system services
crond 2>/dev/null || true
