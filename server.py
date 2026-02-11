#!/usr/bin/env python3
"""
TCC Bridge — Creator Mode Server
Ghost Protocol: Auth-gated, stealth 404s, no fingerprints.
"""
from flask import Flask, send_file, request, jsonify, Response
import logging, os, time

app = Flask(__name__)

# ── GHOST MODE: Kill all default logging ──
log = logging.getLogger('werkzeug')
log.setLevel(logging.CRITICAL)

# ── Stealth Headers ──
FAKE_SERVER = "nginx/1.18.0 (Ubuntu)"
FAKE_404 = """<html>
<head><title>404 Not Found</title></head>
<body>
<center><h1>404 Not Found</h1></center>
<hr><center>nginx/1.18.0 (Ubuntu)</center>
</body>
</html>"""

FAKE_403 = """<html>
<head><title>403 Forbidden</title></head>
<body>
<center><h1>403 Forbidden</h1></center>
<hr><center>nginx/1.18.0 (Ubuntu)</center>
</body>
</html>"""

AUTH_KEY = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")

def ghost_response(body, status=404, content_type="text/html"):
    """Return a response that looks like nginx, not Flask."""
    r = Response(body, status=status, content_type=content_type)
    r.headers["Server"] = FAKE_SERVER
    r.headers.pop("X-Powered-By", None)
    return r

def check_auth():
    """Verify X-Auth header. Returns True if authorized."""
    return request.headers.get("X-Auth") == AUTH_KEY

# ── Routes ──

@app.route("/")
def home():
    if not check_auth():
        return ghost_response(FAKE_404, 404)
    try:
        return send_file("index.html")
    except:
        return ghost_response(FAKE_404, 404)

@app.route("/voice")
def voice():
    if not check_auth():
        return ghost_response(FAKE_404, 404)
    try:
        return send_file("voice.html")
    except:
        return ghost_response(FAKE_404, 404)

@app.route("/health")
def health():
    if not check_auth():
        return ghost_response(FAKE_404, 404)
    return jsonify({"status": "ok", "version": "4.0"})

@app.route("/proof.jpg")
def proof():
    if not check_auth():
        return ghost_response(FAKE_403, 403)
    try:
        return send_file("proof.jpg", mimetype="image/jpeg")
    except:
        return ghost_response(FAKE_404, 404)

# ── Catch-all: Everything else is dead nginx ──
@app.errorhandler(404)
def not_found(e):
    return ghost_response(FAKE_404, 404)

@app.errorhandler(405)
def method_not_allowed(e):
    return ghost_response(FAKE_404, 404)

if __name__ == "__main__":
    print("[GHOST] Bridge online. Port 5000. Auth required.")
    app.run(host="0.0.0.0", port=5000, debug=False)
