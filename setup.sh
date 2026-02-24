
#!/bash/sh
echo "Initiating Sovereignty Bridge Setup..."
pkg update && pkg upgrade -y
pkg install -y python ndk-sysroot clang make libjpeg-turbo termux-api cronie

pip install requests

mkdir -p ~/tcc-bridge
cd ~/tcc-bridge

# Add to crontab
(crontab -l ; echo "*/5 * * * * ~/tcc-bridge/push_state.sh") | crontab -

echo "Setup Complete. Permanent Bridge Active."
