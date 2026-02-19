#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# TCC Bridge V2 - Termux:Boot Auto-Start Script
# Location: ~/.termux/boot/tcc-bridge
#
# This file is executed automatically by the Termux:Boot app whenever
# the Android device boots. It resurrects the pm2 process list so that
# the bridge and cloudflared tunnel start without any manual intervention.
#
# Requirements:
#   - Termux:Boot app installed (F-Droid)
#   - pm2 installed (npm install -g pm2)
#   - pm2 save must have been run after last 'pm2 start'
# =============================================================================

# Wait for Android to finish booting before we do anything.
# 15 seconds is usually safe; increase to 20-30 on slow devices.
sleep 15

# Source Termux profile to ensure PATH includes npm globals, python, etc.
source /data/data/com.termux/files/usr/etc/profile 2>/dev/null || true
source "$HOME/.bashrc" 2>/dev/null || true

# Acquire a CPU wakelock so Android doesn't kill our processes.
# termux-wake-lock is provided by the Termux:API app.
termux-wake-lock 2>/dev/null || true

# Log boot event
LOG_FILE="$HOME/tcc-bridge/logs/boot.log"
mkdir -p "$HOME/tcc-bridge/logs"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Termux:Boot triggered. Resurrecting pm2..." >> "$LOG_FILE"

# Attempt to resurrect saved pm2 process list.
# If the dump file doesn't exist, fall back to starting from ecosystem config.
if pm2 resurrect >> "$LOG_FILE" 2>&1; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] pm2 resurrect succeeded." >> "$LOG_FILE"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] pm2 resurrect failed. Starting from ecosystem config..." >> "$LOG_FILE"
  ECOSYSTEM="$HOME/tcc-bridge/ecosystem.config.js"
  if [[ -f "$ECOSYSTEM" ]]; then
    pm2 start "$ECOSYSTEM" >> "$LOG_FILE" 2>&1 && \
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] pm2 start from ecosystem succeeded." >> "$LOG_FILE" || \
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] pm2 start from ecosystem FAILED." >> "$LOG_FILE"
    pm2 save --force >> "$LOG_FILE" 2>&1 || true
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ecosystem.config.js not found at $ECOSYSTEM" >> "$LOG_FILE"
  fi
fi

# Save updated pm2 state
pm2 save --force >> "$LOG_FILE" 2>&1 || true

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Boot script complete." >> "$LOG_FILE"
