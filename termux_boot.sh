#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
cd ~/tcc-bridge
pm2 start ecosystem.config.js
pm2 save
