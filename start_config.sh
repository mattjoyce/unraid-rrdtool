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

echo "[start] starting busybox crond in foreground"
exec crond -f -l 8
