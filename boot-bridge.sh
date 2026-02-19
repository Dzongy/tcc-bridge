#!/bin/bash
# Termux:Boot script for TCC Bridge
termux-wake-lock
cd ~/tcc-bridge
./watchdog-v2.sh &
cloudflared tunnel run zenith-phone &
