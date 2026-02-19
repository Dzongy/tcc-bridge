#!/data/data/com.termux/files/usr/bin/sh
# kael-boot-bridge.sh — AUTO-START ON REBOOT
# Place in ~/.termux/boot/

# Start PM2 with the Kael Bridge ecosystem
pm2 resurrect || pm2 start ~/tcc-bridge/kael-ecosystem.config.js
