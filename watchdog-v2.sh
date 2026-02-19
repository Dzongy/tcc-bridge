#!/data/data/com.termux/files/usr/bin/bash
# TCC Watchdog V2
# Ensures PM2 is running and manages logs

LOG_FILE="$HOME/tcc/logs/watchdog.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "Watchdog starting..."

while true; do
    # Check if PM2 is alive
    if ! pm2 ping > /dev/null 2>&1; then
        log "PM2 not responding. Restarting..."
        pm2 resurrect || pm2 start ecosystem.config.js
    fi

    # Check disk space
    DISK_USAGE=$(df . | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 90 ]; then
        log "Disk space low ($DISK_USAGE%). Clearing logs..."
        pm2 flush
        rm -rf $HOME/tcc/logs/*.log.*
    fi

    sleep 60
done
