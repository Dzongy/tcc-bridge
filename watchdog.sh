#!/data/data/com.termux/files/usr/bin/sh
# TCC Bridge Watchdog - Process Guardian
while true; do
  if ! pgrep -f "bridge.py" > /dev/null; then
    echo "$(date) - Bridge DOWN. Restarting..."
    pm2 restart tcc-bridge || python3 ~/tcc-bridge/bridge.py &
  fi
  sleep 60
done
