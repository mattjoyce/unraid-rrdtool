# rrdtool-graphs — Unraid-friendly sensor collection and graphing (Dockerized)

A minimal, robust stack that collects host sensor readings from Unraid, stores them in an RRD database, and renders PNG graphs on a schedule. Designed to be readable and supportable by an LLM admin helper.

---

## 1) What this is

- **RRD storage**: `/data/cpu_stats.rrd`  
- **Graphs**: `/data/graphs/*.png`  
- **Config-driven**: `/config/config.json`  
- **Host `/sys` mounted** at `/hostsys` inside the container so Linux hwmon symlinks resolve reliably  
- **Busybox crond** runs collection and graphing on intervals defined in config

Why it works on Unraid: hwmon device indices like `hwmon0`, `hwmon1` can change on each boot. We avoid brittle indices by mounting full `/sys` and resolving sensors by **chip name** at runtime.

---

## 2) Design highlights

- **Stable paths via placeholders**: use `{k10temp}`, `{nct6797}` or `{nct6775}` in config paths.  
  Example: `/hostsys/{k10temp}/temp1_input`
- **Runtime resolution**: `path_resolver.py` maps placeholders to real directories by reading `/hostsys/class/hwmon/hwmon*/name`
- **Config schema** includes `unit`, `transform`, and split graphs by scale
- **Cron** drives collection every 5 min and graphing every 15 min by default

---

## 3) Directory layout (host)

```
/mnt/user/appdata/rrdtool-graphs/
├─ Dockerfile
├─ start_config.sh
├─ crontab
├─ collect_config.py
├─ graph_config.py
├─ init_config.py
├─ path_resolver.py
├─ diags.py
├─ config/
│  └─ config.json
└─ data/
   └─ graphs/
```

---

## 4) Data flow

1. **Mount `/sys`** from host into container at `/hostsys` (read-only).  
2. **Resolve sensor paths** with `path_resolver.py` using chip names.  
3. **Collect** with `collect_config.py`: read sensors, apply `transform`, `rrdtool update` with `N:…`.  
4. **Graph** with `graph_config.py`: `rrdtool graph` to PNGs based on config.  
5. **Cron** runs both on schedule.  
6. **Diags** with `diags.py` to validate mounts, resolver, sensors, RRD, and cron quickly.

---

## 5) Config schema

`/config/config.json` example:

```json
{
  "schema_version": 1,
  "collection": { "interval_seconds": 300 },
  "rrd_path": "/data/cpu_stats.rrd",
  "sensors": [
    {
      "id": "cpu_temp",
      "name": "CPU Temp",
      "unit": "°C",
      "path": "/hostsys/{k10temp}/temp1_input",
      "transform": "value / 1000",
      "min": 0,
      "max": 150
    },
    {
      "id": "cpu_fan",
      "name": "CPU Fan",
      "unit": " rpm",
      "path": "/hostsys/{nct6797}/fan4_input",
      "transform": "value",
      "min": 0,
      "max": 10000
    },
    {
      "id": "sys_temp",
      "name": "System Temp",
      "unit": "°C",
      "path": "/hostsys/{nct6797}/temp2_input",
      "transform": "value / 1000",
      "min": 0,
      "max": 150
    },
    {
      "id": "case_fan",
      "name": "Case Fan",
      "unit": " rpm",
      "path": "/hostsys/{nct6797}/fan2_input",
      "transform": "value",
      "min": 0,
      "max": 5000
    }
  ],
  "rrd": {
    "step": 300,
    "archives": [
      { "cf": "AVERAGE", "xff": 0.5, "steps": 1,  "rows": 288 },
      { "cf": "AVERAGE", "xff": 0.5, "steps": 6,  "rows": 336 },
      { "cf": "AVERAGE", "xff": 0.5, "steps": 24, "rows": 372 },
      { "cf": "MAX",     "xff": 0.5, "steps": 1,  "rows": 288 },
      { "cf": "MIN",     "xff": 0.5, "steps": 1,  "rows": 288 }
    ]
  },
  "graphs": [
    {
      "output": "/data/graphs/temps_day.png",
      "title": "Temperatures — Day",
      "start": "-1d",
      "end": "now",
      "width": 1000,
      "height": 300,
      "series": [
        { "id": "cpu_temp", "color": "#ff0000", "legend": "CPU Temp (°C)" },
        { "id": "sys_temp", "color": "#00aaff", "legend": "System Temp (°C)" }
      ]
    },
    {
      "output": "/data/graphs/fans_day.png",
      "title": "Fans — Day",
      "start": "-1d",
      "end": "now",
      "width": 1000,
      "height": 300,
      "series": [
        { "id": "cpu_fan",  "color": "#00aa00", "legend": "CPU Fan (rpm)" },
        { "id": "case_fan", "color": "#aa00aa", "legend": "Case Fan (rpm)" }
      ]
    },
    {
      "output": "/data/graphs/temps_week.png",
      "title": "Temperatures — Week",
      "start": "-7d",
      "end": "now",
      "width": 1000,
      "height": 300,
      "series": [
        { "id": "cpu_temp", "color": "#ff0000", "legend": "CPU Temp (°C)" },
        { "id": "sys_temp", "color": "#00aaff", "legend": "System Temp (°C)" }
      ]
    },
    {
      "output": "/data/graphs/fans_week.png",
      "title": "Fans — Week",
      "start": "-7d",
      "end": "now",
      "width": 1000,
      "height": 300,
      "series": [
        { "id": "cpu_fan",  "color": "#00aa00", "legend": "CPU Fan (rpm)" },
        { "id": "case_fan", "color": "#aa00aa", "legend": "Case Fan (rpm)" }
      ]
    }
  ]
}
```

Notes:
- `id` is the RRD **DS name**. Changing it after RRD creation desynchronizes graphs.  
- `transform` is a simple expression with `value` in scope. Use carefully.

---

## 6) Build and run

**Key points in Dockerfile:**
- Installs `python3`, `rrdtool`, `busybox`, `tzdata`, `jq`
- Copies scripts to `/scripts`
- Ensures `PYTHONPATH=/scripts` for cron
- Entrypoint: `start_config.sh` creates RRD if missing, starts `crond -f`

**Run** from project root:

```bash
docker rm -f rrdtool-graphs 2>/dev/null || true
docker build -t rrdtool-graphs:latest .

docker run -d   --name rrdtool-graphs   --restart unless-stopped   -e TZ=Australia/Sydney   -e PYTHONPATH=/scripts   -v "$PWD/config:/config"   -v "$PWD/data:/data"   --mount type=bind,source=/sys,target=/hostsys,readonly   rrdtool-graphs:latest
```

Why full `/sys` instead of `/sys/class/hwmon`: `hwmon*` entries are actually symlinks into device paths under `/sys/devices/...`. Mounting all of `/sys` makes those symlinks valid inside the container.

---

## 7) Cron schedule (inside the container)

`/etc/crontabs/root`:

```text
PYTHONPATH=/scripts
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/scripts

# Collect every 5 minutes
*/5  * * * * python3 /scripts/collect_config.py >> /proc/1/fd/1 2>&1

# Graph every 15 minutes
*/15 * * * * python3 /scripts/graph_config.py   >> /proc/1/fd/1 2>&1
```

To view logs live:
```bash
docker logs -f rrdtool-graphs
```

---

## 8) Admin quick commands

Inside the container:

**Overall health:**
```bash
python3 /scripts/diags.py
```

**Force a collect:**
```bash
python3 /scripts/collect_config.py
rrdtool lastupdate /data/cpu_stats.rrd
```

**Force graphs:**
```bash
python3 /scripts/graph_config.py
ls -l /data/graphs
```

**Raw RRD structure & recent rows:**
```bash
rrdtool info /data/cpu_stats.rrd | egrep "^(ds\.|step|last_update|rra\[|pdp_per_row|rows)"
rrdtool lastupdate /data/cpu_stats.rrd
rrdtool fetch /data/cpu_stats.rrd AVERAGE --resolution 300 -s -2h -e now | head -n 40
```

**CSV-like export for all 4 series:**
```bash
rrdtool xport --start -2h --end now   DEF:temp_cpu=/data/cpu_stats.rrd:cpu_temp:AVERAGE   XPORT:temp_cpu:"cpu_temp"   DEF:temp_sys=/data/cpu_stats.rrd:sys_temp:AVERAGE   XPORT:temp_sys:"sys_temp"   DEF:fan_cpu=/data/cpu_stats.rrd:cpu_fan:AVERAGE     XPORT:fan_cpu:"cpu_fan"   DEF:fan_case=/data/cpu_stats.rrd:case_fan:AVERAGE   XPORT:fan_case:"case_fan" | head -n 60
```

Do not use short vnames like `cf` in `xport` because that collides with RRDTool's internal `CF` token.

---

## 9) Common issues and fixes

- **Graphs appear blank but `lastupdate` shows real numbers**  
  1. You might be graphing a time window mostly full of `NaN`.  
  2. DS names in `DEF:` might not match RRD’s DS names.  
  Fix:  
  - Wait at least one full `step` (300 s) so consolidated data exists.  
  - Run `rrdtool info /data/cpu_stats.rrd | grep '^ds\['` to confirm DS names.

- **Sensor file not found**  
  Usually means `/sys` wasn’t mounted to `/hostsys`.  
  Validate with:  
  ```bash
  for d in /hostsys/class/hwmon/hwmon*; do printf "%s -> " "$d"; cat "$d/name"; done
  ```

- **DS names changed in config**  
  RRD keeps the original DS list. If you change `id` names in `sensors[]` after first creation, the RRD won't magically rename them.  
  Fix options:  
  - Revert to the original IDs, or  
  - Delete `/data/cpu_stats.rrd` and restart the container so it can recreate a new RRD with the new DS names.

- **Cron not running**  
  Check that `PYTHONPATH=/scripts` is in the crontab header, and check logs with `docker logs -f rrdtool-graphs`.

- **No PNGs**  
  Make sure `/data/graphs` exists and is writable. `graph_config.py` should `mkdir -p` that path, but if the host bind mount is read-only or missing, PNGs will not save.

---

## 10) Rebuild from scratch

If things are badly out of sync:

```bash
docker rm -f rrdtool-graphs 2>/dev/null || true
rm -f data/cpu_stats.rrd

docker build -t rrdtool-graphs:latest .

docker run -d   --name rrdtool-graphs   --restart unless-stopped   -e TZ=Australia/Sydney   -e PYTHONPATH=/scripts   -v "$PWD/config:/config"   -v "$PWD/data:/data"   --mount type=bind,source=/sys,target=/hostsys,readonly   rrdtool-graphs:latest
```

This forces a clean RRD with your current sensor list.

---

## 11) Extending

- **Add sensors**  
  Add another block to `sensors[]` with a new `id`, `name`, `unit`, `{chip}`-style path under `/hostsys`, and `transform`.  
  Then either recreate the RRD or accept that old RRD will not have that DS.

- **Add more graphs**  
  Add more objects to `graphs[]`. You can group signals by scale (temps in one, fans in another).  
  You can also insert thresholds using `HRULE:80#FF4444:"Temp limit"` for visual warning lines.

- **Dated snapshots**  
  You can add an additional graph entry that writes a timestamped filename (for historical archive), or wrap `rrdtool graph` in a simple timestamping shell/Python helper.

---

## 12) Mental model

- Config describes **what to read** and **what to draw**.  
- Resolver makes sensor file paths stable across reboot.  
- Collector runs every 5 minutes and writes to an RRD.  
- Grapher runs every 15 minutes and turns that RRD into PNGs.  
- Cron keeps time.  
- Diags explains the state.

This gives you persistent telemetry from bare metal into something human-friendly, without relying on Unraid’s own plugin ecosystem yet, and without fragile hwmon indices.  
