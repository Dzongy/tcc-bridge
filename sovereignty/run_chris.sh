#!/bin/bash
# run_chris.sh â TCC Sovereignty Wrapper
trap "" INT
cd /data/data/com.termux/files/home/tcc-bridge/sovereignty
exec python3 -c "
import signal
signal.signal(signal.SIGINT, signal.SIG_IGN)
import runpy
runpy.run_path('chris_core.py', run_name='__main__')
"
