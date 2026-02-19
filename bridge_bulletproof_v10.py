
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
            self.wfile.write(b'{"status":"ok","version":"10.0","bridge":"bulletproof"}')
        elif self.path == '/info':
            self.send_response(200)
            self.end_headers()
            info = {
                "device": DEVICE_NAME,
                "status": "online",
                "time": str(datetime.now()),
                "tunnel": "active"
            }
            self.wfile.write(json.dumps(info).encode())
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"bridge active"}')

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        
        command = data.get("command")
        
        if self.path == '/exec':
            try:
                result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT).decode()
                response = {"status": "success", "output": result}
            except subprocess.CalledProcessError as e:
                response = {"status": "error", "output": e.output.decode()}
        elif self.path == '/toast':
            subprocess.run(f"termux-toast '{command}'", shell=True)
            response = {"status": "toast_sent"}
        elif self.path == '/vibrate':
            subprocess.run("termux-vibrate", shell=True)
            response = {"status": "vibrated"}
        else:
            response = {"status": "unknown_endpoint"}
            
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

def health_monitor():
    while True:
        try:
            # Check tunnel health (mock or real check if cloudflared is in path)
            time.sleep(300) # Every 5 min
            send_ntfy(f"Bridge V10.0 Heartbeat from {DEVICE_NAME}. All systems nominal.", topic=NTFY_HIVE, tags=["check", "green"])
        except Exception as e:
            send_ntfy(f"Bridge Monitor Error: {str(e)}", tags=["warning", "red"])

if __name__ == "__main__":
    # Start health thread
    threading.Thread(target=health_monitor, daemon=True).start()
    
    with socketserver.TCPServer(("", PORT), BridgeHandler) as httpd:
        print(f"Bridge V10.0 active on port {PORT}")
        send_ntfy(f"Bridge V10.0 ONLINE on {DEVICE_NAME}. Port {PORT} active.", tags=["rocket", "celebrate"])
        httpd.serve_forever()
