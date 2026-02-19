#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
cd ~/tcc-bridge
pm2 resurrect || pm2 start ecosystem.v2.config.js
pm2 save
