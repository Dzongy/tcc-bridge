#!/data/data/com.termux/files/usr/bin/bash
# Bridge V2 Boot Script
# Location: ~/.termux/boot/start-tcc.sh
sleep 15
termux-wake-lock
pm2 resurrect
