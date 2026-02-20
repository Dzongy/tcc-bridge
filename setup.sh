#!/bin/bash
# Bridge v2 Setup for Termux

echo "Starting Bridge v2 Setup..."

# Install dependencies
pkg update && pkg upgrade -y
pkg install -y python python-pip termux-api cronie

# Install python requests
pip install requests

# Set permissions
chmod +x push_state.sh

# Setup crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * $(pwd)/push_state.sh") | crontab -

# Start cron daemon
pgrep crond > /dev/null || crond

echo "Bridge v2 Setup Complete. First push incoming..."
./push_state.sh
echo "Verify at https://ntfy.sh/zenith-escape"
