#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot script for TCC Bridge
termux-wake-lock
pm2 resurrect || pm2 start ecosystem.config.js
