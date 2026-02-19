#!/bin/bash
termux-wake-lock
cd ~/tcc-bridge
pm2 start ecosystem.config.js
pm2 save
