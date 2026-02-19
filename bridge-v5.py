
import http.server
import socketserver
import subprocess
import threading
import time
import os
import requests
import json
from datetime import datetime

# CONFIG
PORT = 8080
NTFY_TOPIC = "zenith-escape"
NTFY_HIVE = "tcc-zenith-hive"
DEVICE_NAME = "TCC-Mobile-01"

def send_ntfy(message, topic=NTFY_TOPIC, tags=["robot", "bridge"]):
    try:
        requests.post(f"https://ntfy.sh/{topic}", 
                     data=message.encode('utf-8'),
                     headers={"Title": "Bridge V2 Alert", "Tags": ",".join(tags)})
    except:
        pass

class BridgeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok","version":"5.0"}')
        elif self.path == '/info':
            self.send_response(200)
            self.end_headers()
            info = {"device": DEVICE_NAME, "uptime": "checking...", "time": str(datetime.now())}
            self.wfile.write(json.dumps(info).encode())
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"bridge active"}')

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"received":true}')

def health_monitor():
    while True:
        # Self-check tunnel or connectivity if needed
        time.sleep(300)

if __name__ == "__main__":
    send_ntfy(f"Bridge V2 starting on {DEVICE_NAME}", tags=["rocket"])
    monitor_thread = threading.Thread(target=health_monitor, daemon=True)
    monitor_thread.start()
    
    with socketserver.TCPServer(("", PORT), BridgeHandler) as httpd:
        print(f"Bridge V2 serving at port {PORT}")
        httpd.serve_forever()
