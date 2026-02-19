#!/bin/bash
# Termux:Boot Script for TCC Bridge
termux-wake-lock
cd ~/tcc-bridge
pm2 resurrect || pm2 start ecosystem.config.js
bash watchdog-v2.sh &
