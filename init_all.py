#!/usr/bin/env python3
"""
Orchestration wrapper for RRD initialization.
Loops through all enabled configs in /config and creates RRDs for each.
"""

import json
from pathlib import Path
import subprocess
import sys

CONFIG_DIR = Path("/config")

def main():
    """Initialize RRDs for all enabled JSON configs in /config. Called once at container startup."""
    config_files = sorted(CONFIG_DIR.glob("*.json"))
    
    if not config_files:
        print("[init_all] No config files found in /config")
        sys.exit(1)
    
    for config_path in config_files:
        try:
            with config_path.open(encoding="utf-8") as f:
                cfg = json.load(f)

            # Skip if disabled
            if not cfg.get("enabled", True):
                print(f"[init_all] Skipping disabled config: {config_path.name}")
                continue

            print(f"\n[init_all] Processing {config_path.name}")
            print("=" * 60)

            # Run init
            result = subprocess.run(
                ["python3", "/scripts/init_config.py", "--config", str(config_path)],
                capture_output=False,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                print(f"[init_all] ERROR: Init failed for {config_path.name}")
                sys.exit(1)
                
        except Exception as e:
            print(f"[init_all] ERROR processing {config_path.name}: {e}")
            sys.exit(1)
    
    print("\n[init_all] Complete")

if __name__ == "__main__":
    main()
