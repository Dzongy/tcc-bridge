#!/data/data/com.termux/files/usr/bin/bash
# watchdog-v2.sh - Infinite vigilance
while true; do
  # Check Bridge
  if ! curl -s localhost:8080/health | grep -q "online"; then
    echo "Bridge offline. Restarting..."
    pm2 restart bridge || pm2 start $HOME/tcc-bridge/bridge.py --name bridge
  fi
  
  # Check Cloudflared
  if ! pm2 status cloudflared | grep -q "online"; then
    echo "Cloudflared offline. Restarting..."
    pm2 restart cloudflared
  fi
  
  # Push state every 10 min (600s)
  python3 $HOME/tcc-bridge/state-push.py
  
  sleep 60
done
