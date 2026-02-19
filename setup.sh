
#!/bin/bash
echo "--- TCC Bridge v2.0 Setup ---"
pkg update -y && pkg upgrade -y
pkg install python requests termux-api cronie -y

mkdir -p ~/tcc-bridge
# Files are pushed via GitHub, so we just set up cron here

(crontab -l 2>/dev/null; echo "*/5 * * * * bash ~/tcc-bridge/push_state.sh") | crontab -
crond

echo "Setup complete. Bridge will push state every 5 minutes."
