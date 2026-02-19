#!/bin/bash
# TCC Bridge Watchdog v2.0
# Monitors tunnel and bridge health, alerts ntfy on failure

NTFY_TOPIC="tcc-zenith-hive"
HEALTH_URL="https://zenith.cosmic-claw.com/health"

while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL")
  if [ "$STATUS" != "200" ]; then
    echo "Bridge health check failed: $STATUS"
    curl -d "â ï¸ TCC Bridge Health Check FAILED (Status: $STATUS). Attempting recovery..." "https://ntfy.sh/$NTFY_TOPIC"
    pm2 restart all
  fi
  sleep 300
done
