#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge Boot Persistence
sleep 15
termux-wake-lock
pm2 resurrect
