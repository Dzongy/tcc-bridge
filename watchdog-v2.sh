#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge Watchdog v10.0.1
while true; do
  if ! curl -s http://localhost:8080/health > /dev/null; then
    pm2 restart tcc-bridge
    curl -X POST https://ntfy.sh/tcc-zenith-hive -d "⚠️ Bridge Unresponsive - Auto-Restarted"
  fi
  sleep 60
done
