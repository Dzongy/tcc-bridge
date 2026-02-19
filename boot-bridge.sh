#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# BRIDGE V2 — BULLETPROOF EDITION
# Termux:Boot Script — ~/.termux/boot/boot-bridge.sh
# ============================================================

LOG="$HOME/.bridge/logs/boot.log"
mkdir -p "$HOME/.bridge/logs"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

log "========================================"
log " BRIDGE V2 BOOT SEQUENCE INITIATED"
log "========================================"

# --- Wait for network connectivity ---
log "Waiting for network..."
MAX_WAIT=120
ELAPSED=0
while ! ping -c 1 -W 2 8.8.8.8 &>/dev/null; do
  if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
    log "ERROR: Network not available after ${MAX_WAIT}s. Aborting boot."
    exit 1
  fi
  sleep 5
  ELAPSED=$((ELAPSED + 5))
  log "Still waiting for network... (${ELAPSED}s elapsed)"
done
log "Network is UP."

# --- Give system a moment to stabilize ---
sleep 3

# --- Source environment ---
export PATH="$PATH:/data/data/com.termux/files/usr/bin"
export HOME="/data/data/com.termux/files/home"

# --- Resurrect PM2 processes ---
log "Resurrecting PM2 processes..."
pm2 resurrect >> "$LOG" 2>&1
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  log "PM2 resurrect SUCCESS."
else
  log "WARNING: PM2 resurrect returned status $STATUS. Attempting fresh start..."
  pm2 start "$HOME/.bridge/ecosystem.config.js" >> "$LOG" 2>&1
  pm2 save >> "$LOG" 2>&1
fi

log "Boot sequence complete."
exit 0