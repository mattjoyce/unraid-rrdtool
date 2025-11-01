#!/usr/bin/env python3
"""Simple CLI wrapper for unraid_disk module. Usage: unraid_disk_info.py <idSb>"""
import sys, json
from unraid_disk import get_drive_info, get_value
idsb = sys.argv[1]
print(json.dumps(get_drive_info(idsb)))
