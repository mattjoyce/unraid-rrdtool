#!/usr/bin/env python3
"""
Generate graphs from the RRD based on config.

- Reads graph specs from config['graphs'].
- Uses config['prefix'] and config['graphs_path'] for output naming.
- Builds DEF lines using sensor 'id' as the DS name.

Usage: graph_config.py --config /config/system.json
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

def load_config(config_path: Path) -> Dict[str, Any]:
    """Load and parse JSON config file."""
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def run_graph(rrd_path: str, graph: Dict[str, Any], sensors: List[Dict[str, Any]],
              prefix: str, graphs_path: str) -> None:
    """Generate a single PNG graph using rrdtool. Filename uses prefix_{filename} pattern."""
    # Build output path: {graphs_path}/{prefix}_{filename}
    filename = graph.get("filename", "graph.png")
    if prefix:
        filename = f"{prefix}_{filename}"
    output = os.path.join(graphs_path, filename)
    
    title  = graph.get("title", "RRD Graph")
    start  = graph.get("start", "-1d")
    end    = graph.get("end", "now")
    width  = str(graph.get("width", 1000))
    height = str(graph.get("height", 300))

    # Make sure output directory exists
    os.makedirs(graphs_path, exist_ok=True)

    # Map id -> DS name (RRD DS names are the sensor ids)
    sensor_ids = {s["id"] for s in sensors}
    series = graph.get("series", [])

    # Build command
    cmd = [
        "rrdtool", "graph", output,
        "--start", start, "--end", end,
        "--width", width, "--height", height,
        "--title", title,
        "--vertical-label", "Value"
    ]

    # Add DEFs once per referenced id
    added_defs = set()
    for s in series:
        sid = s["id"]
        if sid not in sensor_ids:
            print(f"[graph] WARN: series id '{sid}' not found in sensors; skipping DEF/LINE")
            continue
        if sid not in added_defs:
            cmd += [f"DEF:{sid}={rrd_path}:{sid}:AVERAGE"]
            added_defs.add(sid)

    # Add LINE statements
    for s in series:
        sid = s["id"]
        if sid not in added_defs:
            continue
        color  = s.get("color", "#000000")
        legend = s.get("legend", sid)
        cmd += [f"LINE1:{sid}{color}:{legend}"]

    print("[graph] CMD:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        print(f"[graph] ERROR: {res.stderr.strip()}")
    else:
        print(f"[graph] Wrote {output}")

def main():
    """CLI entry point for single-config graphing."""
    parser = argparse.ArgumentParser(description="Generate graphs from RRD")
    parser.add_argument("--config", type=Path, required=True, help="Path to config JSON file")
    args = parser.parse_args()
    
    if not args.config.exists():
        print(f"[graph] Error: Config file not found: {args.config}")
        sys.exit(1)
    
    cfg = load_config(args.config)
    
    # Check if enabled
    if not cfg.get("enabled", True):
        print(f"[graph] {args.config.name} is disabled, skipping")
        return
    
    rrd_path = cfg.get("rrd_path")
    graphs = cfg.get("graphs", [])
    sensors = cfg.get("sensors", [])
    prefix = cfg.get("prefix", "")
    graphs_path = cfg.get("graphs_path", "/data/graphs")

    if not rrd_path:
        print("[graph] ERROR: rrd_path not found in config")
        return

    for g in graphs:
        run_graph(rrd_path, g, sensors, prefix, graphs_path)

if __name__ == "__main__":
    main()
