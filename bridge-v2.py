import os
import subprocess
import json
import base64
import time
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIG ---
PORT = 8080
BRIDGE_VERSION = "5.0-V2"
LOG_FILE = "bridge-v2.log"

def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(formatted + "\n")
    except:
        pass

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "online",
        "version": BRIDGE_VERSION,
        "uptime": time.time() - start_time,
        "device": os.uname().nodename
    })

@app.route('/exec', methods=['POST'])
def execute():
    data = request.json
    command = data.get("command")
    if not command:
        return jsonify({"error": "No command provided"}), 400
    
    try:
        log(f"Executing: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return jsonify({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "code": result.returncode
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/toast', methods=['POST'])
def toast():
    msg = request.json.get("message", "Bridge ping")
    subprocess.run(f"termux-toast '{msg}'", shell=True)
    return jsonify({"success": True})
@app.route('/speak', methods=['POST'])
def speak():
    msg = request.json.get("message", "Bridge operational")
    subprocess.run(f"termux-tts-speak '{msg}'", shell=True)
    return jsonify({"success": True})
@app.route('/vibrate', methods=['POST'])
def vibrate():
    duration = request.json.get("duration", 500)
    subprocess.run(f"termux-vibrate -d {duration}", shell=True)
    return jsonify({"success": True})
@app.route('/write_file', methods=['POST'])
def write_file():
    data = request.json
    path = data.get("path")
    content = data.get("content")
    is_base64 = data.get("base64", False)
    
    if not path or content is None:
        return jsonify({"error": "Missing path or content"}), 400
    
    try:
        if is_base64:
            content_bytes = base64.b64decode(content)
            mode = "wb"
        else:
            content_bytes = content
            mode = "w"
            
        with open(path, mode) as f:
            f.write(content_bytes)
        return jsonify({"success": True, "path": path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    start_time = time.time()
    log(f"TCC Bridge V{BRIDGE_VERSION} starting on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
