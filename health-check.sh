#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# TCC Bridge V2 - Health Check Script
# Checks if the public tunnel URL is responding.
# If not, alerts via ntfy and optionally restarts pm2 apps.
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------
PUBLIC_URL="https://zenith.cosmic-claw.com/health"
LOCAL_URL="http://localhost:8765/health"
NTFY_ALERT_URL="https://ntfy.sh/tcc-zenith-hive"
NTFY_OPS_URL="https://ntfy.sh/zenith-escape"
DEVICE_ID="amos-arms"
TIMEOUT=15
LOG_FILE="$HOME/tcc-bridge/logs/health-check.log"
# How many consecutive failures before we restart pm2?
RESTART_THRESHOLD=3
STATE_FILE="/tmp/tcc_health_fail_count"
# -----------------------------------------------------------------------------

mkdir -p "$HOME/tcc-bridge/logs"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

send_ntfy() {
  local title="$1"
  local message="$2"
  local priority="${3:-default}"
  local tags="${4:-bridge}"
  curl -sf \
    -H "Title: $title" \
    -H "Priority: $priority" \
    -H "Tags: $tags" \
    -d "$message" \
    "$NTFY_ALERT_URL" > /dev/null 2>&1 || true
}

get_fail_count() {
  if [[ -f "$STATE_FILE" ]]; then
    cat "$STATE_FILE"
  else
    echo 0
  fi
}

set_fail_count() {
  echo "$1" > "$STATE_FILE"
}

# --- Check public tunnel URL -------------------------------------------------
log "Checking public URL: $PUBLIC_URL"

if curl -sf --max-time "$TIMEOUT" "$PUBLIC_URL" > /dev/null 2>&1; then
  # SUCCESS - tunnel is up
  PREV_FAILS=$(get_fail_count)
  set_fail_count 0

  if [[ "$PREV_FAILS" -ge 1 ]]; then
    log "Tunnel RECOVERED after $PREV_FAILS consecutive failure(s)."
    send_ntfy \
      "â Bridge Tunnel RECOVERED" \
      "Tunnel back online after $PREV_FAILS failure(s).\nURL: $PUBLIC_URL\nDevice: $DEVICE_ID" \
      "default" \
      "white_check_mark,bridge"
  else
    log "Tunnel OK."
  fi
  exit 0
fi

# FAILURE - tunnel did not respond
FAIL_COUNT=$(get_fail_count)
FAIL_COUNT=$((FAIL_COUNT + 1))
set_fail_count "$FAIL_COUNT"

log "Tunnel FAILED (attempt $FAIL_COUNT / $RESTART_THRESHOLD). URL: $PUBLIC_URL"

# Also check local bridge to distinguish bridge crash vs tunnel crash
LOCAL_OK=false
if curl -sf --max-time 5 "$LOCAL_URL" > /dev/null 2>&1; then
  LOCAL_OK=true
  log "Local bridge is UP - tunnel/cloudflared issue only."
else
  log "Local bridge is also DOWN - bridge process likely crashed."
fi

# Send failure alert
send_ntfy \
  "ð¨ Bridge Tunnel DOWN (fail #$FAIL_COUNT)" \
  "Public URL failed health check.\nURL: $PUBLIC_URL\nLocal bridge OK: $LOCAL_OK\nDevice: $DEVICE_ID\nFail count: $FAIL_COUNT/$RESTART_THRESHOLD" \
  "urgent" \
  "rotating_light,skull"

# If we've hit the threshold, attempt a pm2 restart
if [[ "$FAIL_COUNT" -ge "$RESTART_THRESHOLD" ]]; then
  log "Fail threshold reached ($FAIL_COUNT). Attempting pm2 restart..."

  if command -v pm2 > /dev/null 2>&1; then
    pm2 restart tcc-bridge >> "$LOG_FILE" 2>&1 || true
    pm2 restart cloudflared >> "$LOG_FILE" 2>&1 || true
    log "pm2 restart issued for tcc-bridge and cloudflared."

    send_ntfy \
      "ð Bridge pm2 Restart Triggered" \
      "Health check triggered pm2 restart after $FAIL_COUNT consecutive failures.\nDevice: $DEVICE_ID" \
      "high" \
      "arrows_counterclockwise,bridge"

    # Reset counter after restart attempt
    set_fail_count 0
  else
    log "pm2 not found - cannot auto-restart."
    send_ntfy \
      "â ï¸ pm2 Not Found - Manual Restart Needed" \
      "pm2 binary not found on PATH. Cannot auto-restart.\nDevice: $DEVICE_ID" \
      "urgent" \
      "warning"
  fi
fi

exit 1
