#!/bin/bash
# TCC Bridge Boot Script - Place in ~/.termux/boot/
# Requirements: Termux:Boot app installed
termux-wake-lock
cd ~/tcc-bridge
pm2 start ecosystem.config.js
pm2 save
