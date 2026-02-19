#!/bin/bash
# Termux:Boot script for TCC Bridge
termux-wake-lock
cd ~/tcc-bridge
pm2 resurrect || pm2 start ecosystem.config.js
pm2 save
