"""
Resolve chip name placeholders like {k10temp} to actual hwmon directories.
Critical for stable sensor paths across reboots since hwmon indices change on Unraid.
"""
from __future__ import annotations
from pathlib import Path
import re

SYS_MOUNT   = Path("/hostsys")                  # host /sys mounted here
HWMON_ROOT  = SYS_MOUNT / "class" / "hwmon"

# Cache mapping: {"k10temp": Path("/hostsys/class/hwmon/hwmon0"), "nct6775": ...}
_chip_map: dict[str, Path] | None = None

def _scan_hwmon() -> dict[str, Path]:
    """Build mapping of chip names to hwmon directories by reading /hostsys/class/hwmon/hwmon*/name files."""
    m: dict[str, Path] = {}
    for d in HWMON_ROOT.glob("hwmon*"):
        name_file = d / "name"
        if name_file.exists():
            try:
                chip = name_file.read_text(encoding="utf-8").strip()
                if chip:
                    m[chip] = d
            except Exception:
                pass
    return m

def _lookup_chip(token: str) -> Path | None:
    """Resolve chip name to hwmon directory. Tries exact match, case-insensitive, then prefix match."""
    global _chip_map
    if _chip_map is None:
        _chip_map = _scan_hwmon()
    if not _chip_map:
        return None
    # exact
    if token in _chip_map:
        return _chip_map[token]
    tcf = token.casefold()
    # case-insensitive exact
    for name, path in _chip_map.items():
        if name.casefold() == tcf:
            return path
    # prefix
    for name, path in _chip_map.items():
        if name.casefold().startswith(tcf):
            return path
    return None

def to_container_path(p: str) -> Path:
    """
    Accepts any of:
      - /sys/class/hwmon/hwmonX/FILE         (host absolute)
      - /hostsys/{chip}/FILE                 (placeholder)
      - /host/{chip}/FILE or /host/hwmonX/   (legacy; normalized)
    Returns a Path within /hostsys that should be readable.
    """
    s = str(p)

    # 1) Host-absolute → /hostsys
    if s.startswith("/sys/"):
        s = s.replace("/sys/", "/hostsys/", 1)

    # 2) Legacy /host/hwmonX → /hostsys/class/hwmon/hwmonX
    if s.startswith("/host/hwmon"):
        s = s.replace("/host/", "/hostsys/class/", 1)

    # 3) Placeholder {chip}
    m = re.search(r"\{([^}]+)\}", s)
    if m:
        chip = m.group(1)
        base = _lookup_chip(chip)
        if base is not None:
            tail = s.split("}", 1)[1].lstrip("/")
            s = str(base / tail)

    # 4) Legacy /host/{chip}/FILE
    if s.startswith("/host/{"):
        # normalize /host/{chip}/ → /hostsys/{chip}/
        s = s.replace("/host/{", "/hostsys/{", 1)
        return to_container_path(s)  # recurse once

    # 5) Resolve symlinks within /hostsys
    try:
        resolved = Path(s).resolve(strict=False)
        # If resolution leaks to container /sys, re-anchor to /hostsys
        if str(resolved).startswith("/sys/"):
            resolved = Path(str(resolved).replace("/sys/", "/hostsys/", 1))
        return resolved
    except Exception:
        return Path(s)
