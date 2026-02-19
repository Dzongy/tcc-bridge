#!/data/data/com.termux/files/usr/bin/bash
# TCC Watchdog v2.0
# Monitors Bridge and Cloudflared

while true; do
  # Check Bridge
  if ! curl -s http://localhost:8080/health > /dev/null; then
    echo "Bridge down! Restarting..."
    pm2 restart bridge
    curl -d "Bridge down on $(hostname)! Restarting..." ntfy.sh/tcc-zenith-hive
  fi
  
  # Check Cloudflared
  if ! pgrep -x "cloudflared" > /dev/null; then
    echo "Cloudflared down! Restarting..."
    pm2 restart watchdog-v2.sh # Placeholder for tunnel restart if managed by pm2
  fi
  
  sleep 60
done
