#!/usr/bin/env python3
"""
Orchestration wrapper for collection.
Loops through all enabled configs in /config and runs collection for each.
"""

import json
from pathlib import Path
import subprocess
import sys

CONFIG_DIR = Path("/config")

def main():
    """Run collection for all enabled JSON configs in /config. Called by cron every minute."""
    config_files = sorted(CONFIG_DIR.glob("*.json"))
    
    if not config_files:
        print("[collect_all] No config files found in /config")
        sys.exit(1)
    
    for config_path in config_files:
        try:
            with config_path.open(encoding="utf-8") as f:
                cfg = json.load(f)

            # Skip if disabled
            if not cfg.get("enabled", True):
                print(f"[collect_all] Skipping disabled config: {config_path.name}")
                continue

            print(f"\n[collect_all] Processing {config_path.name}")
            print("=" * 60)

            # Run collection
            result = subprocess.run(
                ["python3", "/scripts/collect_config.py", "--config", str(config_path)],
                capture_output=False,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                print(f"[collect_all] ERROR: Collection failed for {config_path.name}")
                
        except Exception as e:
            print(f"[collect_all] ERROR processing {config_path.name}: {e}")
    
    print("\n[collect_all] Complete")

if __name__ == "__main__":
    main()
