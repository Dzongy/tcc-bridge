#!/data/data/com.termux/files/usr/bin/sh
# Infinite loop to monitor tunnel health
while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://zenith.cosmic-claw.com/health)
  if [ "$STATUS" != "200" ]; then
    echo "Tunnel DOWN (Status: $STATUS). Alerting..."
    curl -d "Bridge Tunnel is DOWN (Status $STATUS)" ntfy.sh/tcc-zenith-hive
  fi
  sleep 300
done
