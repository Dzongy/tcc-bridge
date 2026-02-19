#!/data/data/com.termux/files/usr/bin/sh
# TCC Bridge v2.0 Cron Wrapper
# Runs bridge_v2.py every 5 minutes via crond

# Configuration
PROJECT_DIR="/data/data/com.termux/files/home/tcc"
LOG_DIR="$project_dir/.bridge"
PID_FILE="${log_dir}/push_state.pid"
LOG_FILE="${log_dir}/bridge.log"
# Ensure log directory exists
[ -d "${log_dir}" ] || mkdir -p "${log_dir}"

# Log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        log "Still running (PID: $PID). Skipping."
        exit 0
    fi
fi

# Start new run
echo $$ > "$PID_FILE"
log "Starting push_state"

# Run bridge
cd "$PROJECT_DIR" || exit 1
python3 bridge_v2.py --once >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

# Clean up
rm "$PID_FILE"

if [ $EXIT_CODE -eq 0 ]; then
    log "Push completed successfully"
else
    log "Push failed with code $EXIT_CODE"
fi

exit $EXIT_CODE
