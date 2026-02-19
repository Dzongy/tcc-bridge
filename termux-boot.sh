#!/data/data/com.termux/files/usr/bin/bash
# Bridge V2 Boot Script
# Location: ~/.termux/boot/start-bridge.sh
sleep 15
termux-wake-lock
pm2 resurrect
pm2 start ~/ecosystem.config.js --env production
