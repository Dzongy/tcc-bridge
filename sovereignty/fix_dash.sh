#!/bin/bash
# fix_dash.sh - Reconfigure PM2 dash to serve from ~/tcc-bridge/sovereignty/
echo "[*] Stopping old dash process..."
pm2 delete dash 2>/dev/null
echo "[*] Starting new dash from ~/tcc-bridge/sovereignty/ on port 9999..."
cd ~/tcc-bridge/sovereignty
pm2 start "python -m http.server 9999" --name dash
pm2 save
echo "[OK] Dashboard now serving from ~/tcc-bridge/sovereignty/ on port 9999"
echo "[*] Open http://localhost:9999 in Edge"
