#!/bin/sh
set -eu

echo "[start] TZ=${TZ:-UTC}"
mkdir -p /data/graphs

# Initialize all enabled RRDs
echo "[start] Initializing RRDs..."
python3 /scripts/init_all.py || {
  echo "[start] init_all.py failed"
  exit 1
}

# Start graph web server in background
echo "[start] Starting graph web server on port 8080..."
python3 /scripts/graph_server.py &
WEBSERVER_PID=$!
echo "[start] Web server started (PID: $WEBSERVER_PID)"

echo "[start] starting busybox crond in foreground"
exec crond -f -l 8
