#!/data/data/com.termux/files/usr/bin/bash
# TCC Bulletproof Auto-Start
termux-wake-lock
sleep 15
pm2 resurrect || {
  cd ~/tcc-bridge
  pm2 start ecosystem.config.js
  pm2 save
}
curl -d "Bridge V2 System Resurrected After Reboot" https://ntfy.sh/tcc-zenith-hive
