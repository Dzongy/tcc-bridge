#!/bin/bash
# Resolve SIGINT crash loop on Termux Python 3.12
trap "" INT
cd /data/data/com.termux/files/home/tcc-bridge/sovereignty
exec python3 -c "import signal; signal.signal(signal.SIGINT, signal.SIG_IGN); import runpy; runpy.run_path('chris_core.py', run_name='__main__')"
