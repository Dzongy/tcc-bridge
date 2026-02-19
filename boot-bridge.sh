#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
pm2 resurrect
cloudflared tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5 &
