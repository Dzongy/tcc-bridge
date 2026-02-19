#!/bin/bash
# Bridge Watchdog v2.0
# Ensures processes are alive and restarts if stuck.

while true; do
    # Check Bridge Port
    if ! nc -z localhost 8080; then
        echo "Bridge port 8080 closed. Restarting bridge..."
        pm2 restart bridge
    fi

    # Check Cloudflared
    if ! pgrep cloudflared > /dev/null; then
        echo "Cloudflared not running. Restarting..."
        pm2 restart cloudflared
    fi

    sleep 60
done
