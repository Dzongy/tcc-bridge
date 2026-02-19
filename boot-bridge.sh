#!/data/data/com.termux/files/usr/bin/bash
# Termux:Boot Script for TCC Bridge
termux-wake-lock
cd ~/tcc-bridge
./watchdog-v2.sh &
