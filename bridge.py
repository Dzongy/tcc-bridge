
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
            info = {"device": DEVICE_NAME, "uptime": "active", "time": str(datetime.now())}
            self.wfile.write(json.dumps(info).encode())
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"bridge active"}')

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            payload = json.loads(post_data)
            action = payload.get('action')
            
            if action == 'exec':
                cmd = payload.get('cmd')
                res = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"status":"success", "output": res}).encode())
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error":"unknown action"}')
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

def run_server():
    with socketserver.TCPServer(("", PORT), BridgeHandler) as httpd:
        print(f"Bridge serving at port {PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    send_ntfy(f"Bridge V2 Core Engine Starting on {DEVICE_NAME}", topic=NTFY_HIVE, tags=["rocket", "check"])
    run_server()
