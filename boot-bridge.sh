#!/data/data/com.termux/files/usr/bin/bash
# Termux:Boot Script
termux-wake-lock
pm2 resurrect
# Ensure sentinel starts
pm2 start tcc-watchdog