#!/data/data/com.termux/files/usr/bin/bash
# Termux:Boot Script
termux-wake-lock
cd ~/tcc-bridge
pm2 resurrect || pm2 start ecosystem-v2-kael.config.js