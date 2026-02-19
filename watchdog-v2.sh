#!/data/data/com.termux/files/usr/bin/bash
while true; do
  if ! curl -s http://localhost:8080/health | grep -q "alive"; then
    echo "Bridge down! Restarting..."
    pm2 restart bridge
    curl -X POST -d "Bridge recovered by Watchdog" https://ntfy.sh/tcc-zenith-hive
  fi
  sleep 60
done
