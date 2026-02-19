#!/bin/bash
# Watchdog for TCC Bridge
while true; do
    if ! pgrep -f "bridge.py" > /dev/null; then
        echo "$(date): Bridge down, restarting..."
        python3 ~/tcc-bridge/bridge.py &
    fi
    sleep 30
done
