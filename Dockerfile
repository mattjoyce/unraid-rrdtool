# syntax=docker/dockerfile:1
FROM alpine:3.20

# 1) Base tools
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-flask \
    rrdtool \
    busybox \
    tzdata \
    jq \
    bash \
    smartmontools

# 2) Runtime layout
WORKDIR /scripts
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/scripts

# 3) Copy scripts (host → image)
# Make sure these exist in the build context (same folder as Dockerfile)
COPY collect_config.py    /scripts/collect_config.py
COPY collect_all.py       /scripts/collect_all.py
COPY graph_config.py      /scripts/graph_config.py
COPY graph_all.py         /scripts/graph_all.py
COPY init_config.py       /scripts/init_config.py
COPY init_all.py          /scripts/init_all.py
COPY path_resolver.py     /scripts/path_resolver.py
COPY theme_loader.py      /scripts/theme_loader.py
COPY diags.py             /scripts/diags.py
COPY disk_temp.py         /scripts/disk_temp.py
COPY start_config.sh      /scripts/start_config.sh
COPY crontab              /etc/crontabs/root

# 3b) Unraid disk info helpers (ini-only logic in module, tiny CLI wrapper)
COPY unraid_disk.py       /scripts/unraid_disk.py
COPY unraid_disk_info.py  /scripts/unraid_disk_info.py

# 3c) Graph web server
COPY graph_server.py      /scripts/graph_server.py
COPY templates/           /scripts/templates/

# 4) Permissions
RUN chmod +x /scripts/*.py /scripts/start_config.sh && \
    mkdir -p /config /data /data/graphs

# 5) Ensure crontab exports PYTHONPATH
RUN grep -q '^PYTHONPATH=/scripts' /etc/crontabs/root || \
    sed -i '1i PYTHONPATH=/scripts' /etc/crontabs/root

# 6) Expose web server port
EXPOSE 8080

# 7) Default command: init, then foreground crond
ENTRYPOINT ["/scripts/start_config.sh"]
