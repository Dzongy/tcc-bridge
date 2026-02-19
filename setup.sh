#!/bin/bash
# Zenith Bridge v2.0 Installer
echo "Starting Zenith Bridge v2.0 Installation..."

# Install dependencies
pkg update && pkg upgrade -y
pkg install -y python termux-api cronie curl

# Install python libs
pip install requests

# Add to crontab (every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * bash ~/push_state.sh >> ~/bridge.log 2>&1") | crontab -

echo "Installation complete. Ensure 'termux-api' app is installed from Play Store/F-Droid."
echo "Run 'bash ~/push_state.sh' to test."
