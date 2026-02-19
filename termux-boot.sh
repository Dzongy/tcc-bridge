#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge â Bulletproof Auto-Start
# This script goes in ~/.termux/boot/

# Wait for network
sleep 10

# Resurrect PM2 processes (Bridge + Tunnel)
export PATH=$PATH:/data/data/com.termux/files/usr/bin
pm2 resurrect

# Send notification
curl -d "Bridge V2 Resurrected after Reboot" https://ntfy.sh/tcc-zenith-hive
