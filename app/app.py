import os
import socket

import redis
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))


def get_redis():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_connect_timeout=2)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Container Lab – Visit Counter</title>
  <style>
    body { font-family: sans-serif; max-width: 700px; margin: 60px auto; padding: 0 20px; }
    .card { background: #f0f4ff; border-radius: 8px; padding: 24px; margin: 16px 0; }
    .label { color: #555; font-size: 0.9em; text-transform: uppercase; }
    .value { font-size: 1.6em; font-weight: bold; color: #1a237e; }
    .error { background: #fff3f3; border-left: 4px solid #e53935; padding: 12px; }
  </style>
</head>
<body>
  <h1>Container Lab – Visit Counter</h1>
  {% if redis_ok %}
  <div class="card">
    <div class="label">Total Visits (stored in Redis)</div>
    <div class="value">{{ visits }}</div>
  </div>
  {% else %}
  <div class="error">
    <strong>Redis not reachable.</strong> Is the redis service running and REDIS_HOST set correctly?
  </div>
  {% endif %}
  <div class="card">
    <div class="label">Container Hostname (who served this request?)</div>
    <div class="value">{{ hostname }}</div>
  </div>
  <div class="card">
    <div class="label">Redis Host (configured via environment variable)</div>
    <div class="value">{{ redis_host }}</div>
  </div>
  <p style="color:#888; font-size:0.85em;">Refresh the page and watch the visit counter increase. Restart the app container – does the count reset?</p>
</body>
</html>
"""


@app.route("/")
def index():
    try:
        r = get_redis()
        visits = r.incr("visits")
        redis_ok = True
    except Exception:
        visits = -1
        redis_ok = False

    return render_template_string(
        HTML_TEMPLATE,
        visits=visits,
        hostname=socket.gethostname(),
        redis_host=REDIS_HOST,
        redis_ok=redis_ok,
    )


@app.route("/health")
def health():
    try:
        r = get_redis()
        r.ping()
        return jsonify({"status": "ok", "redis": "connected", "instance": socket.gethostname()}), 200
    except Exception as e:
        return jsonify({"status": "degraded", "redis": str(e), "instance": socket.gethostname()}), 503


@app.route("/reset", methods=["POST"])
def reset():
    try:
        r = get_redis()
        r.delete("visits")
        return jsonify({"status": "reset", "instance": socket.gethostname()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
