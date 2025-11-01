#!/usr/bin/env python3
"""Resolve disk identifiers and report temperatures via smartctl. Supports serial numbers, WWN, UUID, and /dev paths."""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

def sh(cmd):
    """Run command with stdout capture, stderr suppressed."""
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False)

def base_disk(dev):
    """Collapse partition paths like /dev/sda1 or /dev/nvme0n1p1 to parent disk."""
    # collapse partitions to parent disk
    if re.match(r"^/dev/nvme\d+n\d+p\d+$", dev):
        return re.sub(r"p\d+$", "", dev)
    if re.match(r"^/dev/sd[a-z]+\d+$", dev):
        return re.sub(r"\d+$", "", dev)
    return dev

def realpath(p):
    """Resolve symlink to real path, return original if resolution fails."""
    try:
        return str(Path(p).resolve())
    except Exception:
        return p

def lsblk_json():
    """Get lsblk output as JSON with all fields."""
    out = sh(["lsblk", "-J", "-O"]).stdout
    return json.loads(out) if out else {"blockdevices": []}

def all_disks():
    """List all disk (not partition) block devices from lsblk."""
    blk = lsblk_json()
    out = []
    def walk(nodes):
        for n in nodes or []:
            if n.get("type") == "disk":
                out.append("/dev/" + n["name"])
            walk(n.get("children"))
    walk(blk.get("blockdevices"))
    return out

def match_from_lsblk(needle):
    """Search lsblk fields (serial, wwn, model, label, uuid) for substring match."""
    nlow = needle.lower()
    blk = lsblk_json()
    hits = set()
    def walk(nodes):
        for n in nodes or []:
            fields = []
            for k in ("name","kname","serial","wwn","model","label","uuid","partuuid","partlabel"):
                v = n.get(k)
                if v: fields.append(str(v).lower())
            # also include by-id symlink name fragments via udev in practice, but lsblk lacks them
            if any(nlow in f for f in fields):
                hits.add("/dev/" + n["name"])
            walk(n.get("children"))
    walk(blk.get("blockdevices"))
    return [base_disk(realpath(x)) for x in hits]

def resolve_fs_selector(spec):
    """Resolve filesystem selector like UUID=xxx or LABEL=xxx to device path."""
    # spec like UUID=..., LABEL=..., PARTUUID=...
    out = sh(["blkid", "-o", "device", "-t", spec]).stdout.strip()
    if out:
        return base_disk(realpath(out))
    return None

def resolve_identifier(idstr):
    """Resolve disk identifier to /dev/sdX or /dev/nvmeXnY. Tries by-id, direct /dev, UUID/LABEL, serial/WWN."""
    # 1) by-id path
    if idstr.startswith("/dev/disk/by-id/"):
        return base_disk(realpath(idstr))
    # 2) direct /dev node
    if idstr.startswith("/dev/"):
        return base_disk(realpath(idstr))
    # 3) FS selectors
    if any(idstr.startswith(p) for p in ("UUID=","LABEL=","PARTUUID=","PARTLABEL=")):
        d = resolve_fs_selector(idstr)
        if d: return d
    # 4) try by-id name contains
    for link in Path("/dev/disk/by-id").glob("*"):
        name = link.name.lower()
        if idstr.lower() in name:
            return base_disk(realpath(str(link)))
    # 5) try Serial or WWN match via lsblk
    hits = match_from_lsblk(idstr)
    if hits:
        # prefer an sdX over partitions if present
        hits = sorted(set(hits))
        return hits[0]
    return None

def smart_temp(dev):
    """
    Returns (model, temp_string). Uses smartctl JSON.
    - Tries not to wake SATA: -n standby first.
    - For NVMe, -n standby is ignored but harmless.
    """
    def run_smart(args):
        r = sh(args)
        if r.returncode == 0 and r.stdout:
            try:
                return json.loads(r.stdout)
            except Exception:
                return None
        return None

    j = run_smart(["smartctl", "-j", "-n", "standby", "-A", dev])
    # If enclosure is picky, retry without -n for NVMe or stubborn bridges
    if not j:
        j = run_smart(["smartctl", "-j", "-A", dev])
    if not j:
        # last-chance, try SAT hint
        j = run_smart(["smartctl", "-d", "sat", "-j", "-n", "standby", "-A", dev])

    if not j:
        return ("unknown", "unavailable")

    # model
    model = j.get("model_name") or j.get("device",{}).get("model_name") or j.get("device",{}).get("name") or "unknown"

    # unified temperature
    temp = None
    tnode = j.get("temperature") or {}
    temp = tnode.get("current")
    if temp is None:
        # may be in SCT status or missing
        if j.get("power_state") == "STANDBY" or j.get("ata_smart_data",{}).get("power_mode") == "STANDBY":
            return (model, "standby")
        # look in attributes 190/194 for legacy cases
        for a in j.get("ata_smart_attributes",{}).get("table",[]):
            if a.get("id") in (190,194):
                temp = a.get("value")
                break
    if temp is None:
        return (model, "unknown")
    return (model, f"{temp}")

def main():
    """CLI entry point for disk temperature utility."""
    ap = argparse.ArgumentParser(description="Resolve disk IDs and report temperature via smartctl")
    ap.add_argument("ids", nargs="+", help="Serial, WWN, /dev/disk/by-id/*, /dev/*, or UUID=/LABEL=/PARTUUID=")
    ap.add_argument("--json", action="store_true", help="Emit JSON array")
    args = ap.parse_args()

    rows = []
    for ident in args.ids:
        dev = resolve_identifier(ident)
        if not dev:
            rows.append({"id": ident, "device": None, "model": None, "temperature": None, "error": "unresolved"})
            continue
        model, temp = smart_temp(dev)
        rows.append({"id": ident, "device": dev, "model": model, "temperature": temp})

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        w = max(8, max(len(r["id"]) for r in rows))
        print(f"{'ID'.ljust(w)}  DEVICE         MODEL                         TEMP")
        print("-"*w + "  -------------  ------------------------------  ----")
        for r in rows:
            print(f"{r['id'].ljust(w)}  {str(r['device'] or '-').ljust(13)}  {str(r['model'] or '-').ljust(30)}  {r['temperature'] or '-'}")

if __name__ == "__main__":
    sys.exit(main())
