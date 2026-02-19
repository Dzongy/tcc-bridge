#!/bin/bash
# TCC Bridge Watchdog V2
while true; do
    if ! curl -s localhost:8080/health | grep -q "OK"; then
        echo "Bridge down! Restarting..."
        curl -d "Bridge down! Restarting..." ntfy.sh/tcc-zenith-hive
        pm2 restart bridge
    fi
    # Check cloudflared
    if ! pgrep cloudflared > /dev/null; then
        echo "Cloudflared down! Restarting..."
        cloudflared tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5 &
    fi
    sleep 300
done
