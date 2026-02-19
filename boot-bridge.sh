#!/data/data/com.termux/files/usr/bin/bash
# Auto-start TCC Bridge on Reboot
termux-wake-lock
pm2 resurrect
