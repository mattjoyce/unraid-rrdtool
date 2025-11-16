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
from typing import Any, Dict, List, Optional
import theme_loader

def load_config(config_path: Path) -> Dict[str, Any]:
    """Load and parse JSON config file."""
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def run_graph(rrd_path: str, graph: Dict[str, Any], sensors: List[Dict[str, Any]],
              prefix: str, graphs_path: str, theme: Optional[Dict[str, Any]] = None) -> None:
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

    # Add theme color and font options if theme is loaded
    if theme:
        theme_colors = theme_loader.get_rrdtool_colors(theme)
        cmd.extend(theme_colors)
        theme_fonts = theme_loader.get_rrdtool_fonts(theme)
        cmd.extend(theme_fonts)

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
        color_ref = s.get("color", "#000000")
        # Resolve named colors (e.g., "PRIMARY") to hex values using theme
        color = theme_loader.resolve_color(color_ref, theme)
        legend = s.get("legend", sid)
        cmd += [f"LINE1:{sid}{color}:{legend}"]

    print("[graph] CMD:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        print(f"[graph] ERROR: {res.stderr.strip()}")
    else:
        print(f"[graph] Wrote {output}")

def generate_theme_env(theme: Dict[str, Any]) -> str:
    """Generate shell export statements from theme dict."""
    lines = []

    # Scaffolding colors
    for key, value in theme.get("scaffolding", {}).items():
        lines.append(f'export THEME_COLOR_{key.upper()}="{value}"')

    # Series colors
    for key, value in theme.get("series", {}).items():
        lines.append(f'export THEME_COLOR_{key.upper()}="{value}"')

    # Alarm colors
    for key, value in theme.get("alarms", {}).items():
        lines.append(f'export THEME_COLOR_{key.upper()}="{value}"')

    # Fonts
    for key, value in theme.get("fonts", {}).items():
        lines.append(f'export THEME_FONT_{key.upper()}="{value}"')

    return "\n".join(lines) + "\n"

def run_custom_graph(graph: Dict[str, Any], config: Dict[str, Any],
                     theme: Optional[Dict[str, Any]] = None) -> None:
    """Execute custom bash script for graph generation."""
    script_path = graph.get("script")
    if not script_path:
        print("[graph] ERROR: Custom graph missing 'script' field")
        return

    # Resolve script path (handle relative paths)
    if not os.path.isabs(script_path):
        script_path = os.path.join("/config", script_path)

    if not os.path.exists(script_path):
        print(f"[graph] ERROR: Custom script not found: {script_path}")
        return

    # Build output path: {graphs_path}/{prefix}_{filename}
    filename = graph.get("filename", "custom_graph.png")
    prefix = config.get("prefix", "")
    if prefix:
        filename = f"{prefix}_{filename}"
    output_file = os.path.join(config["graphs_path"], filename)

    # Make sure output directory exists
    os.makedirs(config["graphs_path"], exist_ok=True)

    # Generate theme env file in /tmp
    theme_env_file = f"/tmp/theme_{config.get('prefix', 'default')}.env"
    if theme:
        with open(theme_env_file, 'w') as f:
            theme_env = generate_theme_env(theme)
            f.write(theme_env)
    else:
        # Create empty theme file
        with open(theme_env_file, 'w') as f:
            f.write("")

    # Build command with positional args
    cmd = [
        script_path,
        config["rrd_path"],                # $1 - RRD_PATH
        output_file,                       # $2 - OUTPUT_PATH
        graph.get("start", "-1d"),         # $3 - START
        graph.get("end", "now"),           # $4 - END
        str(graph.get("width", 1200)),     # $5 - WIDTH
        str(graph.get("height", 400)),     # $6 - HEIGHT
        theme_env_file                     # $7 - THEME_ENV_FILE
    ]

    # Execute script
    print(f"[graph] Running custom script: {script_path}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode == 0:
        print(f"[graph] Created: {output_file}")
        if result.stdout:
            print(f"[graph] Script output: {result.stdout.strip()}")
    else:
        print(f"[graph] ERROR: Custom script failed with code {result.returncode}")
        if result.stderr:
            print(f"[graph] {result.stderr.strip()}")

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
    theme_name = cfg.get("theme")

    if not rrd_path:
        print("[graph] ERROR: rrd_path not found in config")
        return

    # Load theme if specified
    theme = None
    if theme_name:
        theme = theme_loader.load_theme(theme_name, config_dir=args.config.parent)
        if not theme:
            print(f"[graph] WARNING: Could not load theme '{theme_name}', using default colors")

    for g in graphs:
        graph_type = g.get("type", "standard")

        if graph_type == "custom":
            # Handle custom graph script
            run_custom_graph(g, cfg, theme)
        else:
            # Handle standard graph
            run_graph(rrd_path, g, sensors, prefix, graphs_path, theme)

if __name__ == "__main__":
    main()
