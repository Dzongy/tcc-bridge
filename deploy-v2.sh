#!/bin/bash
# ONE-TAP DEPLOY FOR BRIDGE V2
echo "Installing Bridge V2..."

pkg update && pkg upgrade -y
pkg install python python-pip curl psmisc -y
pip install requests

mkdir -p ~/tcc-bridge
cd ~/tcc-bridge

echo "Setup complete. Start with: bash watchdog-v2.sh"