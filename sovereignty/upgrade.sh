#!/bin/bash
# Zenith Upgrade Script - pulls latest and restarts all services
echo "=========================================="
echo " ZENITH UPGRADE IN PROGRESS..."
echo "=========================================="
cd ~/tcc-bridge && git pull
echo "[1/3] Code pulled from GitHub"
pm2 restart mega-harvest 2>/dev/null || pm2 start sovereignty/mega_harvester.py --name mega-harvest --interpreter python3
echo "[2/3] MegaHarvester + Chat Server restarted"
pm2 restart agi 2>/dev/null || pm2 start sovereignty/zenith_agi_core.py --name agi --interpreter python3
echo "[3/3] AGI Core started"
pm2 save
echo "=========================================="
echo " ZENITH UPGRADED. All systems live."
echo " Chat server: http://localhost:8888/chat"
echo " AGI core: running"
echo "=========================================="
pm2 list
