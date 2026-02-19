#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge Boot Script
termux-wake-lock
sleep 10
cd $HOME/tcc-bridge
pm2 resurrect || pm2 start ecosystem.config.js
pm2 save
