#!/bin/bash
echo "--- TCC SOVEREIGNTY FIX — SIGINT RECOVERY ---"
cd /data/data/com.termux/files/home/tcc-bridge
# 1. Discard local changes (to ensure git pull works)
git checkout -- .
# 2. Pull latest fixes
git pull origin main
# 3. Restart PM2 processes with new config
pm2 delete all
pm2 start ecosystem.config.js
# 4. Save and setup startup
pm2 save
echo "--- FIX APPLIED ---"
pm2 status
