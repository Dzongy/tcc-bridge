#!/bin/bash
trap "" INT
cd /data/data/com.termux/files/home/tcc-bridge/sovereignty
exec python3 -u zenith_core.py
