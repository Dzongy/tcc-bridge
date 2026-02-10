#!/data/data/com.termux/files/usr/bin/bash
# AMOS Bridge Watchdog â keeps bridge.py alive forever
while true; do
    echo "[WATCHDOG] Starting bridge.py..."
    cd ~/tcc-bridge && git pull origin main 2>/dev/null
    python bridge.py
    echo "[WATCHDOG] Bridge crashed. Restarting in 3 seconds..."
    sleep 3
done
