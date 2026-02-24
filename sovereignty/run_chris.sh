#!/bin/bash
trap "" INT
cd /data/data/com.termux/files/home/tcc-bridge/sovereignty
# Use setsid to run python in a new session, detaching from the caller's process group
import signal
signal.signal(signal.SIGINT, signal.SIG_IGN)
import runpy
runpy.run_path('chris_core.py', run_name='__main__')
"
