#!/usr/bin/env python3
"""
rrdtool-graphs diagnostics for multi-config system

Checks:
  - Python environment and resolver
  - Mount points (/hostsys, /var/local/emhttp, /config, /data)
  - Config files (discovery, validation, enabled status)
  - For each config:
    - Source type and sensor resolution
    - RRD existence and health
    - Recent data points
    - Graph file existence
  - Cron status and schedule
  
Outputs clear PASS/FAIL lines and actionable recommendations.
"""

from __future__ import annotations
import os, sys, json, subprocess, shlex, time, argparse
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

RESULTS: List[Dict[str, Any]] = []

def add_result(name: str, ok: bool, detail: str = "", data: Any = None):
    """Record a diagnostic check result."""
    RESULTS.append({"check": name, "ok": ok, "detail": detail, "data": data})

def run(cmd: str, timeout: int = 5) -> subprocess.CompletedProcess:
    """Run shell command with timeout."""
    return subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout, check=False)

def bold(s: str) -> str:
    """Return ANSI bold text."""
    return f"\033[1m{s}\033[0m"

# ---------- 1) Environment ----------
def check_env():
    """Verify TZ and PYTHONPATH environment variables."""
    print(bold("\n=== 1. ENVIRONMENT ==="))
    tz = os.environ.get("TZ", "")
    pypath = os.environ.get("PYTHONPATH", "")
    add_result("env.TZ", bool(tz), f"TZ={tz!r}")
    add_result("env.PYTHONPATH", "/scripts" in pypath, f"PYTHONPATH={pypath!r}")

# ---------- 2) Mounts ----------
def check_mounts():
    """Verify /hostsys, /var/local/emhttp, /config, /data mounts and check for available hwmon chips."""
    print(bold("\n=== 2. MOUNT POINTS ==="))
    mounts = Path("/proc/mounts").read_text(encoding="utf-8").splitlines()
    
    # Check /hostsys
    has_hostsys = any(" /hostsys " in line for line in mounts)
    add_result("mounts./hostsys", has_hostsys, "Full /sys mounted at /hostsys")
    
    if has_hostsys and Path("/hostsys/class/hwmon").exists():
        chips = []
        for d in Path("/hostsys/class/hwmon").glob("hwmon*"):
            name_file = d / "name"
            if name_file.exists():
                try:
                    chip = name_file.read_text().strip()
                    chips.append(f"{d.name}={chip}")
                except:
                    pass
        add_result("mounts.hwmon_chips", len(chips) > 0, ", ".join(chips))
    
    # Check /var/local/emhttp
    has_emhttp = any(" /var/local/emhttp " in line for line in mounts)
    add_result("mounts./var/local/emhttp", has_emhttp, "Unraid emhttp dir mounted")
    
    if has_emhttp:
        disks_ini = Path("/var/local/emhttp/disks.ini")
        exists = disks_ini.exists()
        age = ""
        if exists:
            mtime = disks_ini.stat().st_mtime
            age = f"modified {int(time.time() - mtime)}s ago"
        add_result("mounts.disks.ini", exists, age)
    
    # Check /config and /data
    add_result("mounts./config", Path("/config").exists(), "Config directory mounted")
    add_result("mounts./data", Path("/data").exists(), "Data directory mounted")

# ---------- 3) Config Discovery ----------
def discover_configs() -> List[Path]:
    """Find and validate all JSON config files in /config directory."""
    print(bold("\n=== 3. CONFIG DISCOVERY ==="))
    config_dir = Path("/config")
    if not config_dir.exists():
        add_result("config.discovery", False, "/config directory not found")
        return []
    
    configs = sorted(config_dir.glob("*.json"))
    add_result("config.discovery", len(configs) > 0, f"Found {len(configs)} config files")
    
    # List them
    for cfg_path in configs:
        try:
            with cfg_path.open() as f:
                cfg = json.load(f)
            enabled = cfg.get("enabled", True)
            schema = cfg.get("schema_version", "unknown")
            prefix = cfg.get("prefix", "?")
            source = cfg.get("collection", {}).get("source_type", "?")
            status = "ENABLED" if enabled else "DISABLED"
            add_result(f"config.{cfg_path.name}", True, 
                      f"{status}, schema={schema}, prefix={prefix}, source={source}")
        except Exception as e:
            add_result(f"config.{cfg_path.name}", False, f"Parse error: {e}")
    
    return configs

# ---------- 4) Resolver ----------
def check_resolver():
    """Test path_resolver module by attempting to resolve a k10temp placeholder."""
    print(bold("\n=== 4. PATH RESOLVER ==="))
    try:
        sys.path.insert(0, "/scripts")
        from path_resolver import to_container_path
        add_result("resolver.import", True, "path_resolver imported")
        
        # Test resolution
        test_path = "/hostsys/{k10temp}/temp1_input"
        try:
            resolved = to_container_path(test_path)
            exists = resolved.exists()
            add_result("resolver.test", exists, f"{test_path} -> {resolved}")
        except Exception as e:
            add_result("resolver.test", False, f"Resolution failed: {e}")
            
    except Exception as e:
        add_result("resolver.import", False, f"Import failed: {e}")

# ---------- 5) Per-Config Validation ----------
def check_config_detail(cfg_path: Path):
    """Validate single config file: check sensors, RRD, and graphs."""
    print(bold(f"\n=== CONFIG: {cfg_path.name} ==="))
    
    try:
        with cfg_path.open() as f:
            cfg = json.load(f)
    except Exception as e:
        add_result(f"{cfg_path.name}.load", False, f"Failed to load: {e}")
        return
    
    # Check if enabled
    enabled = cfg.get("enabled", True)
    if not enabled:
        add_result(f"{cfg_path.name}.enabled", False, "Config is DISABLED")
        return
    
    add_result(f"{cfg_path.name}.enabled", True, "Config is ENABLED")
    
    # Basic structure
    rrd_path = cfg.get("rrd_path")
    add_result(f"{cfg_path.name}.rrd_path", bool(rrd_path), rrd_path or "MISSING")
    
    source_type = cfg.get("collection", {}).get("source_type", "sysfs")
    add_result(f"{cfg_path.name}.source_type", True, source_type)
    
    sensors = cfg.get("sensors", [])
    add_result(f"{cfg_path.name}.sensors.count", len(sensors) > 0, f"{len(sensors)} sensors")
    
    # Check sensors based on source type
    if source_type == "sysfs":
        check_sysfs_sensors(cfg_path.name, sensors)
    elif source_type == "unraid_disk":
        check_disk_sensors(cfg_path.name, sensors)
    
    # Check RRD
    if rrd_path:
        check_rrd_detail(cfg_path.name, rrd_path, sensors)
    
    # Check graphs
    graphs = cfg.get("graphs", [])
    check_graphs(cfg_path.name, cfg, graphs)

def check_sysfs_sensors(config_name: str, sensors: List[Dict]):
    """Test all sysfs sensors by reading values and applying transforms."""
    print(f"\n  → Checking sysfs sensors...")
    sys.path.insert(0, "/scripts")
    from path_resolver import to_container_path
    from collect_config import apply_transform

    all_ok = True
    details = []
    for s in sensors:
        sid = s.get("id", "?")
        name = s.get("name", sid)
        try:
            path = to_container_path(s["path"])
            exists = path.exists()
            if exists:
                raw = path.read_text(encoding="utf-8").strip()
                val = float(raw)
                val = apply_transform(val, s.get("transform"))
                unit = s.get("unit", "")
                details.append(f"{name}: {val}{unit} ✓")
            else:
                details.append(f"{name}: PATH NOT FOUND ✗")
                all_ok = False
        except Exception as e:
            details.append(f"{name}: ERROR {e} ✗")
            all_ok = False
    
    add_result(f"{config_name}.sensors.sysfs", all_ok, "\n    ".join(details))

def check_disk_sensors(config_name: str, sensors: List[Dict]):
    """Test all unraid_disk sensors by reading from disks.ini."""
    print(f"\n  → Checking disk sensors...")
    sys.path.insert(0, "/scripts")
    from unraid_disk import get_value
    
    all_ok = True
    details = []
    for s in sensors:
        sid = s.get("id", "?")
        name = s.get("name", sid)
        disk_id = s.get("disk_id")
        
        if not disk_id:
            details.append(f"{name}: MISSING disk_id ✗")
            all_ok = False
            continue
        
        try:
            temp = get_value(disk_id, "temp")
            if temp:
                unit = s.get("unit", "")
                details.append(f"{name}: {temp}{unit} ✓")
            else:
                details.append(f"{name}: NO TEMP DATA ✗")
                all_ok = False
        except Exception as e:
            details.append(f"{name}: ERROR {e} ✗")
            all_ok = False
    
    add_result(f"{config_name}.sensors.disks", all_ok, "\n    ".join(details))

def check_rrd_detail(config_name: str, rrd_path: str, sensors: List[Dict]):
    """Verify RRD exists, check DS names match config, and fetch recent data."""
    print(f"\n  → Checking RRD...")
    rrd = Path(rrd_path)
    
    if not rrd.exists():
        add_result(f"{config_name}.rrd.exists", False, f"{rrd_path} NOT FOUND")
        return
    
    add_result(f"{config_name}.rrd.exists", True, f"{rrd_path} exists")
    
    # Check last update
    res = run(f"rrdtool last {shlex.quote(rrd_path)}")
    if res.returncode == 0:
        last_ts = int(res.stdout.strip())
        age = int(time.time() - last_ts)
        age_str = f"{age}s ago"
        if age < 600:  # less than 10 minutes
            add_result(f"{config_name}.rrd.last_update", True, age_str)
        else:
            add_result(f"{config_name}.rrd.last_update", False, f"STALE: {age_str}")
    else:
        add_result(f"{config_name}.rrd.last_update", False, "rrdtool last failed")
    
    # Check data points
    res = run(f"rrdtool lastupdate {shlex.quote(rrd_path)}")
    if res.returncode == 0:
        lines = res.stdout.strip().split('\n')
        if len(lines) >= 2:
            header = lines[0]
            last_values = lines[1] if len(lines) > 1 else ""
            has_data = "nan" not in last_values.lower() and last_values.strip() != ""
            add_result(f"{config_name}.rrd.data", has_data, 
                      f"Latest: {last_values[:80]}")
    
    # Check DS count matches sensor count
    res = run(f"rrdtool info {shlex.quote(rrd_path)} | grep -c '^ds\\['")
    if res.returncode == 0:
        ds_count = int(res.stdout.strip())
        sensor_count = len(sensors)
        match = ds_count == sensor_count
        add_result(f"{config_name}.rrd.ds_count", match, 
                  f"RRD has {ds_count} DS, config has {sensor_count} sensors")

def check_graphs(config_name: str, cfg: Dict, graphs: List[Dict]):
    """Verify all PNG graph files exist with correct prefix_{filename} pattern."""
    print(f"\n  → Checking graphs...")
    prefix = cfg.get("prefix", "")
    graphs_path = cfg.get("graphs_path", "/data/graphs")
    
    if not graphs:
        add_result(f"{config_name}.graphs.defined", False, "No graphs defined")
        return
    
    add_result(f"{config_name}.graphs.defined", True, f"{len(graphs)} graphs defined")
    
    missing = []
    found = []
    for g in graphs:
        filename = g.get("filename", "unknown.png")
        if prefix:
            filename = f"{prefix}_{filename}"
        full_path = Path(graphs_path) / filename
        
        if full_path.exists():
            size = full_path.stat().st_size
            age = int(time.time() - full_path.stat().st_mtime)
            found.append(f"{filename} ({size} bytes, {age}s old)")
        else:
            missing.append(filename)
    
    if missing:
        add_result(f"{config_name}.graphs.files", False, 
                  f"Missing: {', '.join(missing)}")
    else:
        add_result(f"{config_name}.graphs.files", True, 
                  f"All {len(found)} graph files exist")

# ---------- 6) Cron ----------
def check_crond():
    """Verify crond is running and crontab has collect_all.py and graph_all.py scheduled."""
    print(bold("\n=== 6. CRON STATUS ==="))
    
    # Is crond running?
    ps = run("pgrep crond")
    running = ps.returncode == 0
    add_result("crond.running", running, f"PID: {ps.stdout.strip()}" if running else "NOT RUNNING")
    
    # Check crontab
    cron = Path("/etc/crontabs/root")
    if cron.exists():
        content = cron.read_text(encoding="utf-8")
        add_result("crond.crontab.exists", True, "Crontab found")
        
        has_collect = "collect_all.py" in content
        has_graph = "graph_all.py" in content
        has_pp = "PYTHONPATH=/scripts" in content
        
        add_result("crond.collect_all", has_collect, "collect_all.py in crontab")
        add_result("crond.graph_all", has_graph, "graph_all.py in crontab")
        add_result("crond.pythonpath", has_pp, "PYTHONPATH set in crontab")
        
        # Show schedule
        lines = [l.strip() for l in content.split('\n') 
                if l.strip() and not l.startswith('#') and not l.startswith('PYTHONPATH') 
                and not l.startswith('SHELL') and not l.startswith('PATH')]
        if lines:
            add_result("crond.schedule", True, "\n    ".join(lines))
    else:
        add_result("crond.crontab.exists", False, "Crontab not found")

# ---------- 7) Summary & Recommendations ----------
def print_summary():
    """Print diagnostic summary with actionable recommendations for any failures."""
    print(bold("\n" + "="*70))
    print(bold("DIAGNOSTIC SUMMARY"))
    print("="*70)
    
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["ok"])
    failed = total - passed
    
    print(f"\nTotal checks: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print(bold("\n✓ ALL CHECKS PASSED"))
        print("\nSystem appears healthy. Graphs should populate as data accumulates.")
        print("Wait 15-30 minutes for meaningful data in graphs.")
        return True
    
    print(bold("\n✗ ISSUES FOUND"))
    print("\nFailed checks:")
    for r in RESULTS:
        if not r["ok"]:
            print(f"  - {r['check']}: {r['detail']}")
    
    # Actionable recommendations
    print(bold("\nRECOMMENDATIONS:"))
    
    # Check for common issues
    mount_issues = [r for r in RESULTS if r['check'].startswith('mounts.') and not r['ok']]
    if mount_issues:
        print("\n  1. MOUNT PROBLEMS:")
        print("     Fix: Ensure container has proper volume mounts")
        print("     docker run -v /sys:/hostsys:ro -v /var/local/emhttp:/var/local/emhttp:ro ...")
    
    config_issues = [r for r in RESULTS if '.sensors.' in r['check'] and not r['ok']]
    if config_issues:
        print("\n  2. SENSOR PROBLEMS:")
        print("     - Check sensor paths in config files")
        print("     - Verify chip names match: ls /hostsys/class/hwmon/*/name")
        print("     - For disks, verify disk_id matches disks.ini")
    
    rrd_issues = [r for r in RESULTS if '.rrd.' in r['check'] and not r['ok']]
    if rrd_issues:
        print("\n  3. RRD PROBLEMS:")
        print("     - If RRD doesn't exist, restart container to trigger init")
        print("     - If stale, check cron is running and collection is working")
        print("     - Manual test: docker exec rrdtool-graphs python3 /scripts/collect_all.py")
    
    cron_issues = [r for r in RESULTS if r['check'].startswith('crond.') and not r['ok']]
    if cron_issues:
        print("\n  4. CRON PROBLEMS:")
        print("     - Verify crond is running as PID 1")
        print("     - Check crontab: docker exec rrdtool-graphs cat /etc/crontabs/root")
        print("     - View logs: docker logs -f rrdtool-graphs")
    
    return False

# ---------- Main ----------
def main():
    """Run full diagnostic suite: environment, mounts, configs, sensors, RRDs, graphs, and cron."""
    ap = argparse.ArgumentParser(description="Comprehensive diagnostics for rrdtool-graphs")
    ap.add_argument("--json", action="store_true", help="Output JSON format")
    ap.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = ap.parse_args()
    
    if not args.json:
        print(bold("="*70))
        print(bold("rrdtool-graphs DIAGNOSTICS"))
        print(bold("="*70))
        print(f"Timestamp: {datetime.now()}")
    
    # Run all checks
    check_env()
    check_mounts()
    configs = discover_configs()
    check_resolver()
    
    for cfg_path in configs:
        check_config_detail(cfg_path)
    
    check_crond()
    
    if args.json:
        print(json.dumps({"results": RESULTS, "timestamp": datetime.now().isoformat()}, indent=2))
    else:
        # Print all results
        print(bold("\n" + "="*70))
        print(bold("DETAILED RESULTS"))
        print("="*70)
        
        for r in RESULTS:
            status = "✓ PASS" if r["ok"] else "✗ FAIL"
            print(f"\n[{status}] {r['check']}")
            if r['detail']:
                # Indent multi-line details
                detail_lines = r['detail'].split('\n')
                for line in detail_lines:
                    print(f"    {line}")
        
        success = print_summary()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
