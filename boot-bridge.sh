#!/data/data/com.termux/files/usr/bin/bash
# TCC Boot Loader
termux-wake-lock
echo "Booting TCC Infrastructure..."
sleep 15
pm2 resurrect || pm2 start $HOME/tcc-bridge/ecosystem.config.js
# Ensure crond is running for other tasks
crond 2>/dev/null || true
