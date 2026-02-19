#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge Watchdog v2.0
while true; do
  if ! curl -s http://localhost:8765/health > /dev/null; then
    echo "$(date): Bridge down! Restarting..."
    pm2 restart bridge || pm2 start bridge.py --name bridge
    curl -d "Bridge self-healed on $(hostname)" https://ntfy.sh/tcc-zenith-hive
  fi
  sleep 60
done
