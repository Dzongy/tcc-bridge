#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge â Bulletproof Auto-Start
termux-wake-lock
sleep 20
pm2 resurrect || {
  cd ~/tcc-bridge
  pm2 start ecosystem.config.js
  pm2 save
}
curl -d "Bridge v6 Resurrected" https://ntfy.sh/tcc-zenith-hive