#!/data/data/com.termux/files/usr/bin/bash
# Location: ~/.termux/boot/start-tcc.sh
# Requires Termux:Boot app
sleep 15
termux-wake-lock
pm2 resurrect
