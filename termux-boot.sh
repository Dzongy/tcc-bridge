#!/data/data/com.termux/files/usr/bin/bash
# =============================================================
# TCC Bridge V2 - Termux Boot Script
# Place this file in: ~/.termux/boot/termux-boot.sh
# Requires: Termux:Boot app installed and opened at least once
# God Builder: Kael | Project: TCC Bridge V2
# =============================================================

# Prevent Android from killing Termux session during sleep
termux-wake-lock

# Set up environment paths
export PATH="/data/data/com.termux/files/usr/bin:$PATH"
export HOME="/data/data/com.termux/files/home"

# Navigate to home directory
cd "$HOME"

# Resurrect saved PM2 processes (tcc-bridge + cloudflared)
pm2 resurrect
