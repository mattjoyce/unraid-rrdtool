#!/usr/bin/env python3
"""Parse Unraid's /var/local/emhttp/disks.ini to retrieve disk info by idSb (serial). No SMART calls, just INI parsing."""

import re, json
from pathlib import Path

DISKS_INI = Path("/var/local/emhttp/disks.ini")

def _parse_disks_ini(path: Path) -> dict:
    data, section = {}, None
    if not path.exists():
        raise FileNotFoundError(f"{path} not found (mount /var/local/emhttp into the container)")
    with path.open(errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith(("#",";")): continue
            m = re.match(r"\[([^\]]+)\]", line)
            if m:
                section = m.group(1).strip()
                data.setdefault(section, {})
                continue
            m = re.match(r'([^=]+)=(.*)', line)
            if m and section:
                k = m.group(1).strip()
                v = m.group(2).strip().strip('"')
                data[section][k] = v
    return data

def get_drive_info(idsb: str) -> dict:
    """Return the full key:value map from disks.ini for the disk whose idSb == idsb."""
    disks = _parse_disks_ini(DISKS_INI)
    for sec, kv in disks.items():
        if kv.get("idSb") == idsb:
            out = dict(kv)
            out.setdefault("_section", sec)
            return out
    raise ValueError(f"idSb '{idsb}' not found in {DISKS_INI}")

def get_value(idsb: str, key: str):
    """Return a single value by key for that idSb, or None if missing."""
    return get_drive_info(idsb).get(key)

