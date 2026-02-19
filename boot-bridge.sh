#!/data/data/com.termux/files/usr/bin/bash
# Termux:Boot script for TCC Bridge
sleep 10
pm2 resurrect || (cd ~/tcc-bridge && pm2 start ecosystem.config.js && pm2 save)
