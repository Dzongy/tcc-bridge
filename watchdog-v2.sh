#!/data/data/com.termux/files/usr/bin/bash
# Watchdog V2 - Keeps the Bridge and Tunnel alive
echo "Watchdog V2 active..."
while true; do
  # Check Bridge (8765)
  if ! nc -z localhost 8765; then
    echo "$(date): Bridge port 8765 not responding. Restarting..."
    pm2 restart tcc-bridge
  fi
  
  # Check Tunnel
  if ! pgrep -x "cloudflared" > /dev/null; then
    echo "$(date): Cloudflared process missing. Restarting..."
    pm2 restart cloudflared
  fi
  
  sleep 60
done
