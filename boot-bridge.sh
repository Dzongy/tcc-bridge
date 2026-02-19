#!/bin/bash
# TCC Boot Script (Termux:Boot compatible)
termux-wake-lock
pm2 resurrect || pm2 start ~/ecosystem.config.js
