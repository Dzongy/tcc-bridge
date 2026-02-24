#!/bin/bash
# TCC Sovereignty Wrapper with SIGINT Protection
trap "" INT
cd /data/data/com.termux/files/home/tcc-bridge/sovereignty
# Use python3 -c to ignore SIGINT before any imports happen
exec python3 -u -c "
import signal
signal.signal(signal.SIGINT, signal.SIG_IGN)
import runpy
runpy.run_path('zenith_core.py', run_name='__main__')
"
