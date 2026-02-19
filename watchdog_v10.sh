
#!/data/data/com.termux/files/usr/bin/sh
while true; do
  if ! pgrep -f "bridge.py" > /dev/null; then
    echo "Bridge down, restarting..."
    pm2 restart bridge
  fi
  if ! pgrep -f "cloudflared" > /dev/null; then
    echo "Cloudflared down, restarting..."
    pm2 restart cloudflared
  fi
  sleep 60
done
