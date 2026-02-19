
#!/bin/bash
# TCC Bridge Cron Wrapper
LOCKFILE="/tmp/tcc_bridge.lock"

if [ -f "$LOCKFILE" ]; then
    echo "Bridge already running."
    exit 1
fi

touch "$LOCKFILE"
python ~/tcc-bridge/bridge_v2.py >> ~/tcc-bridge/bridge.log 2>&1
rm "$LOCKFILE"
