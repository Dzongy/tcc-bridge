#!/bin/bash
# Zenith Bridge Cron Script
PIDFILE="/tmp/zenith_bridge.pid"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if ps -p "$PID" > /dev/null; then
        echo "Bridge already running."
        exit 1
    fi
fi

echo $$ > "$PIDFILE"
python3 ~/bridge_v2.py
rm "$PIDFILE"
