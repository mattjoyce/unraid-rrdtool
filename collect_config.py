#!/usr/bin/env python3
"""
Collect sensor readings and update the RRD.

Supports multiple source types:
- sysfs: reads from /hostsys/{chip}/sensor_input files
- unraid_disk: reads from /var/local/emhttp/disks.ini via unraid_disk module

Usage: collect_config.py --config /config/system.json
"""

import argparse
import ast
import json
import operator
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

def load_config(config_path: Path) -> Dict[str, Any]:
    """Load and parse JSON config file."""
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def apply_transform(value: float, expr: str | None) -> float:
    """
    Safe transform evaluator. Supports arithmetic operations only.
    Example: "value / 1000" or "value * 2 + 10"
    """
    if not expr:
        return value

    # Whitelist of safe operators
    safe_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def eval_node(node):
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Num):  # Python 3.7 compatibility
            return node.n
        elif isinstance(node, ast.Name):
            if node.id == "value":
                return value
            raise ValueError(f"Unknown variable: {node.id}")
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in safe_operators:
                raise ValueError(f"Unsupported operation: {type(node.op).__name__}")
            left = eval_node(node.left)
            right = eval_node(node.right)
            return safe_operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            if type(node.op) not in safe_operators:
                raise ValueError(f"Unsupported operation: {type(node.op).__name__}")
            operand = eval_node(node.operand)
            return safe_operators[type(node.op)](operand)
        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")

    try:
        tree = ast.parse(expr, mode='eval')
        return float(eval_node(tree.body))
    except (ValueError, SyntaxError, TypeError) as e:
        raise ValueError(f"Invalid transform expression '{expr}': {e}") from e

def read_sysfs_sensor(sensor: Dict[str, Any]) -> float | None:
    """Read sensor from /hostsys path"""
    from path_resolver import to_container_path

    label = sensor.get("name", sensor.get("id", "unknown"))
    unit = sensor.get("unit", "")
    try:
        path = to_container_path(sensor["path"])
        raw = Path(path).read_text(encoding="utf-8").strip()
        val = float(raw)
        val = apply_transform(val, sensor.get("transform"))
        print(f"{label}: {val}{unit}")
        return val
    except Exception as e:
        print(f"[collect] Error reading {label}: {e}")
        return None

def read_unraid_disk_sensor(sensor: Dict[str, Any]) -> float | None:
    """Read disk field from disks.ini (temp, numReads, numWrites, etc.)"""
    from unraid_disk import get_value

    label = sensor.get("name", sensor.get("id", "unknown"))
    unit = sensor.get("unit", "")
    disk_id = sensor.get("disk_id")
    field = sensor.get("field", "temp")  # Default to temperature for backwards compatibility

    if not disk_id:
        print(f"[collect] Error: {label} missing disk_id")
        return None

    try:
        field_str = get_value(disk_id, field)
        if field_str is None:
            print(f"[collect] {label}: no {field} data")
            return None
        # Handle non-numeric values (e.g., "*" for spun down disks)
        if field_str == "*" or field_str == "-":
            print(f"[collect] {label}: {field}={field_str} (skipping)")
            return None
        val = float(field_str)
        val = apply_transform(val, sensor.get("transform"))
        # COUNTER/DERIVE types need integers, not floats
        ds_type = sensor.get("ds_type", "GAUGE")
        if ds_type in ("COUNTER", "DERIVE", "ABSOLUTE"):
            val = int(val)
        print(f"{label}: {val}{unit}")
        return val
    except ValueError as e:
        print(f"[collect] Error parsing {label} {field}='{field_str}': {e}")
        return None
    except Exception as e:
        print(f"[collect] Error reading {label}: {e}")
        return None

def read_sensor(sensor: Dict[str, Any], source_type: str) -> float | None:
    """Dispatch to appropriate reader based on source_type"""
    if source_type == "sysfs":
        return read_sysfs_sensor(sensor)
    elif source_type == "unraid_disk":
        return read_unraid_disk_sensor(sensor)
    else:
        print(f"[collect] Unknown source_type: {source_type}")
        return None

def update_rrd(config_path: Path):
    """Read all sensors from config and update the RRD with current values."""
    cfg = load_config(config_path)
    
    # Check if enabled
    if not cfg.get("enabled", True):
        print(f"[collect] {config_path.name} is disabled, skipping")
        return
    
    source_type = cfg.get("collection", {}).get("source_type", "sysfs")
    
    # Read all sensors
    values: List[str] = []
    for s in cfg["sensors"]:
        v = read_sensor(s, source_type)
        values.append("U" if v is None else str(v))

    # Update RRD
    rrd_values = "N:" + ":".join(values)
    rrd_path = cfg.get("rrd_path")
    
    if not rrd_path:
        print(f"[collect] Error: rrd_path missing in {config_path.name}")
        return
    
    cmd = ["rrdtool", "update", rrd_path, rrd_values]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode == 0:
        print(f"{datetime.now():%Y-%m-%d %H:%M:%S} - RRD updated OK: {config_path.name}")
    else:
        print(f"[collect] RRD update error for {config_path.name}: {result.stderr.strip()}")

def main():
    """CLI entry point for single-config collection."""
    parser = argparse.ArgumentParser(description="Collect sensor data and update RRD")
    parser.add_argument("--config", type=Path, required=True, help="Path to config JSON file")
    args = parser.parse_args()
    
    if not args.config.exists():
        print(f"[collect] Error: Config file not found: {args.config}")
        sys.exit(1)
    
    update_rrd(args.config)

if __name__ == "__main__":
    main()
