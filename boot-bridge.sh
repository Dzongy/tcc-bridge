#!/data/data/com.termux/files/usr/bin/sh
# Bridge V2 Boot Script
termux-wake-lock
# Wait for network
sleep 10
# Start PM2 processes
pm2 resurrect
