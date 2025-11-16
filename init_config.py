#!/usr/bin/env python3
"""
Initialize RRD database from config.

Usage: init_config.py --config /config/system.json
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

def load_config(config_path: Path):
    """Load and parse JSON config file."""
    with config_path.open('r', encoding='utf-8') as f:
        return json.load(f)

def create_rrd(config_path: Path):
    """Create RRD database from config if it doesn't already exist."""
    config = load_config(config_path)
    
    # Check if enabled
    if not config.get("enabled", True):
        print(f"[init] {config_path.name} is disabled, skipping")
        return
    
    rrd_path = config.get('rrd_path')
    if not rrd_path:
        print(f"[init] ERROR: rrd_path missing in {config_path.name}")
        sys.exit(1)
    
    # Check if RRD already exists
    if Path(rrd_path).exists():
        print(f"[init] RRD already exists: {rrd_path}")
        return
    
    # Build the RRD create command
    step = config['rrd']['step']
    cmd = ['rrdtool', 'create', rrd_path]
    cmd.extend(['--step', str(step)])
    
    # Add data sources from sensors
    for sensor in config['sensors']:
        min_val = sensor.get('min', 0)
        max_val = sensor.get('max', 'U')
        ds_type = sensor.get('ds_type', 'GAUGE')  # Support GAUGE, COUNTER, DERIVE, ABSOLUTE
        # DS:name:type:heartbeat:min:max
        ds = f"DS:{sensor['id']}:{ds_type}:{step*2}:{min_val}:{max_val}"
        cmd.append(ds)
    
    # Add archives
    for archive in config['rrd']['archives']:
        cf = archive['cf']
        xff = archive['xff']
        steps = archive['steps']
        rows = archive['rows']
        rra = f"RRA:{cf}:{xff}:{steps}:{rows}"
        cmd.append(rra)
    
    print(f"[init] Creating RRD: {rrd_path}")
    print(f"[init] Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    if result.returncode == 0:
        print(f"[init] RRD database created successfully: {rrd_path}")
    else:
        print(f"[init] Error creating RRD: {result.stderr}")
        sys.exit(1)

def main():
    """CLI entry point for single-config RRD initialization."""
    parser = argparse.ArgumentParser(description="Initialize RRD database")
    parser.add_argument("--config", type=Path, required=True, help="Path to config JSON file")
    args = parser.parse_args()
    
    if not args.config.exists():
        print(f"[init] Error: Config file not found: {args.config}")
        sys.exit(1)
    
    create_rrd(args.config)

if __name__ == "__main__":
    main()
