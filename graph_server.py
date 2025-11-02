#!/usr/bin/env python3
"""Simple web server to display RRD graphs."""
from __future__ import annotations

import os
from pathlib import Path
from flask import Flask, render_template, send_from_directory

app = Flask(__name__)

GRAPHS_PATH = Path("/data/graphs")


@app.route("/")
def index():
    """Display all available graphs grouped by prefix."""
    if not GRAPHS_PATH.exists():
        return render_template("index.html", graph_groups={})

    # Group graphs by prefix (e.g., "system_", "disks_")
    graphs = {}
    for graph_file in sorted(GRAPHS_PATH.glob("*.png")):
        # Extract prefix (everything before first underscore)
        parts = graph_file.stem.split("_", 1)
        prefix = parts[0] if len(parts) > 1 else "other"

        if prefix not in graphs:
            graphs[prefix] = []
        graphs[prefix].append(graph_file.name)

    return render_template("index.html", graph_groups=graphs)


@app.route("/graphs/<path:filename>")
def serve_graph(filename):
    """Serve graph image files."""
    return send_from_directory(GRAPHS_PATH, filename)


@app.route("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "graphs_path": str(GRAPHS_PATH)}


if __name__ == "__main__":
    # Create graphs directory if it doesn't exist
    GRAPHS_PATH.mkdir(parents=True, exist_ok=True)

    # Run server
    port = int(os.environ.get("GRAPH_SERVER_PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
