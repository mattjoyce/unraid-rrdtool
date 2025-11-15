# Custom Graph Type Implementation Plan

## Overview

Add support for custom bash scripts to generate complex RRDtool graphs (Cacti/Nagios-style) while maintaining backwards compatibility with existing JSON-based simple graphs.

## Motivation

Complex graph types (stacked areas, inverted IO, mixed line+area, etc.) are difficult to express in JSON. Rather than expanding JSON complexity, allow users to write bash scripts that use full RRDtool power directly.

## Architecture Decisions

### Graph Types
- **Standard (default)**: Existing JSON-based simple line graphs - continue to work as-is
- **Custom (new)**: Bash script-based graphs for complex visualizations

### Script Storage
- User-specified paths in JSON config (absolute or relative)
- Recommended location: `/config/custom_graphs/` or `/scripts/graphs/`

### Parameter Passing
- **Positional arguments** for essential params: `RRD_PATH OUTPUT_PATH START END WIDTH HEIGHT THEME_ENV_FILE`
- **Environment variables** for theme colors/fonts (via sourcing generated env file)

### Theme Integration
- Create helper script to convert JSON theme → shell env vars
- Custom scripts can source theme env file to get colors/fonts
- Scripts can override theme vars if needed

## Implementation Components

### 1. Theme Helper Script: `scripts/theme_to_env.sh`

**Purpose**: Convert JSON theme file to sourceable shell environment variables

**Input**: Theme JSON file path (e.g., `/config/themes/unraid-dark.json`)

**Output**: Shell export statements to stdout

**Example output**:
```bash
export THEME_NAME="Unraid Dark Theme"
export THEME_COLOR_BACK="#0F1115"
export THEME_COLOR_CANVAS="#0B0E14"
export THEME_COLOR_FRAME="#2A2F3A"
export THEME_COLOR_FONT="#E6E8EB"
export THEME_COLOR_AXIS="#A6ADB7"
export THEME_COLOR_GRID="#3A404880"
export THEME_COLOR_MGRID="#545B66B3"
export THEME_COLOR_ARROW="#A6ADB7"
export THEME_COLOR_PRIMARY="#FF6A00"
export THEME_COLOR_AMBER="#FFB100"
export THEME_COLOR_GREEN="#34D399"
export THEME_COLOR_RED="#F43F5E"
export THEME_COLOR_ACCENT="#3B82F6"
export THEME_COLOR_WARN_HRULE="#FF4D00CC"
export THEME_COLOR_CRITICAL_HRULE="#FFD166CC"
export THEME_FONT_DEFAULT="11"
export THEME_FONT_TITLE="13"
export THEME_FONT_AXIS="10"
export THEME_FONT_LEGEND="11"
```

**Implementation notes**:
- Use Python with `json` and `sys` modules (keep consistent with existing codebase)
- Flatten nested JSON structure into `THEME_*` env vars
- Handle color names with proper escaping for shell

---

### 2. Modify `graph_config.py`

**Current flow** (for standard graphs):
```python
for graph in config["graphs"]:
    # Build rrdtool command from JSON
    # Execute: subprocess.run(["rrdtool", "graph", ...])
```

**New flow** (add custom graph detection):
```python
for graph in config["graphs"]:
    graph_type = graph.get("type", "standard")

    if graph_type == "custom":
        # NEW: Handle custom graph
        run_custom_graph(graph, config, theme)
    else:
        # EXISTING: Handle standard graph
        run_graph(graph, config, theme)
```

**New function: `run_custom_graph()`**:
```python
def run_custom_graph(graph, config, theme):
    """Execute custom bash script for graph generation"""

    script_path = graph.get("script")
    if not script_path:
        print(f"ERROR: Custom graph missing 'script' field")
        return

    # Resolve script path (handle relative paths)
    if not os.path.isabs(script_path):
        script_path = os.path.join("/config", script_path)

    if not os.path.exists(script_path):
        print(f"ERROR: Custom script not found: {script_path}")
        return

    # Build output path
    output_file = os.path.join(
        config["graphs_path"],
        f"{config['prefix']}_{graph['filename']}"
    )

    # Generate theme env file in /tmp
    theme_env_file = f"/tmp/theme_{config['prefix']}.env"
    if theme:
        with open(theme_env_file, 'w') as f:
            theme_env = generate_theme_env(theme)
            f.write(theme_env)

    # Build command with positional args
    cmd = [
        script_path,
        config["rrd_path"],           # $1 - RRD_PATH
        output_file,                  # $2 - OUTPUT_PATH
        graph.get("start", "-1d"),    # $3 - START
        graph.get("end", "now"),      # $4 - END
        str(graph.get("width", 1200)), # $5 - WIDTH
        str(graph.get("height", 400)), # $6 - HEIGHT
        theme_env_file                # $7 - THEME_ENV_FILE
    ]

    # Execute script
    print(f"Running custom graph: {script_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"  Created: {output_file}")
    else:
        print(f"  ERROR: {result.stderr}")
```

**Helper function: `generate_theme_env()`**:
```python
def generate_theme_env(theme):
    """Generate shell export statements from theme dict"""
    lines = []

    # Scaffolding colors
    for key, value in theme.get("scaffolding", {}).items():
        lines.append(f'export THEME_COLOR_{key.upper()}="{value}"')

    # Series colors
    for key, value in theme.get("series", {}).items():
        lines.append(f'export THEME_COLOR_{key.upper()}="{value}"')

    # Alarm colors
    for key, value in theme.get("alarms", {}).items():
        lines.append(f'export THEME_COLOR_{key.upper()}="{value}"')

    # Fonts
    for key, value in theme.get("fonts", {}).items():
        lines.append(f'export THEME_FONT_{key.upper()}="{value}"')

    return "\n".join(lines) + "\n"
```

---

### 3. Example Custom Graph Script: `examples/nic_io.sh`

**Purpose**: Demonstrate complex graph with inverted download traffic (Cacti-style)

**Location**: `examples/nic_io.sh` (users copy to `/config/custom_graphs/`)

**Script structure**:
```bash
#!/bin/sh
# Custom graph: Network IO with inverted download (Cacti-style)
#
# Positional arguments:
#   $1 = RRD_PATH       (e.g., /data/network.rrd)
#   $2 = OUTPUT_PATH    (e.g., /data/graphs/system_nic_io_day.png)
#   $3 = START          (e.g., -1d)
#   $4 = END            (e.g., now)
#   $5 = WIDTH          (e.g., 1200)
#   $6 = HEIGHT         (e.g., 400)
#   $7 = THEME_ENV_FILE (e.g., /tmp/theme_system.env)

RRD_PATH="$1"
OUTPUT="$2"
START="${3:--1d}"
END="${4:-now}"
WIDTH="${5:-1200}"
HEIGHT="${6:-400}"
THEME_ENV="$7"

# Source theme environment variables
if [ -f "$THEME_ENV" ]; then
    . "$THEME_ENV"
fi

# Set defaults if theme not loaded
: ${THEME_COLOR_BACK:="#FFFFFF"}
: ${THEME_COLOR_CANVAS:="#F5F5F5"}
: ${THEME_COLOR_FONT:="#000000"}
: ${THEME_COLOR_GREEN:="#00AA00"}
: ${THEME_COLOR_ACCENT:="#0000AA"}
: ${THEME_FONT_DEFAULT:="11"}
: ${THEME_FONT_TITLE:="13"}

# Build rrdtool graph command with complex options
rrdtool graph "$OUTPUT" \
  --start "$START" --end "$END" \
  --width "$WIDTH" --height "$HEIGHT" \
  --title "Network IO - eth0" \
  --vertical-label "Bytes/sec" \
  --color BACK"${THEME_COLOR_BACK}" \
  --color CANVAS"${THEME_COLOR_CANVAS}" \
  --color FONT"${THEME_COLOR_FONT}" \
  --font DEFAULT:"${THEME_FONT_DEFAULT}" \
  --font TITLE:"${THEME_FONT_TITLE}" \
  --lower-limit 0 \
  --rigid \
  DEF:rx_bytes="$RRD_PATH:eth0_rx_bytes:AVERAGE" \
  DEF:tx_bytes="$RRD_PATH:eth0_tx_bytes:AVERAGE" \
  CDEF:rx_neg=rx_bytes,-1,* \
  AREA:rx_neg"${THEME_COLOR_GREEN}":"Download" \
  GPRINT:rx_bytes:LAST:"Current\:%8.2lf %sB/s" \
  GPRINT:rx_bytes:AVERAGE:"Avg\:%8.2lf %sB/s" \
  GPRINT:rx_bytes:MAX:"Max\:%8.2lf %sB/s\n" \
  AREA:tx_bytes"${THEME_COLOR_ACCENT}":"Upload  " \
  GPRINT:tx_bytes:LAST:"Current\:%8.2lf %sB/s" \
  GPRINT:tx_bytes:AVERAGE:"Avg\:%8.2lf %sB/s" \
  GPRINT:tx_bytes:MAX:"Max\:%8.2lf %sB/s\n" \
  HRULE:0"${THEME_COLOR_FONT}":""

echo "Generated: $OUTPUT"
```

**Additional examples to create**:
- `examples/disk_temps_stacked.sh` - Stacked area graph for multiple disks
- `examples/cpu_load_mixed.sh` - Mixed line + area graph
- `examples/temps_with_thresholds.sh` - Graph with HRULE warning lines

---

### 4. Update Configuration Examples

**Example config entry** (add to `config/system.json` or new config):
```json
{
  "graphs": [
    {
      "filename": "cpu_temps_12h.png",
      "title": "CPU Temperatures — 12 hours",
      "start": "-12h",
      "end": "now",
      "width": 1200,
      "height": 400,
      "series": [
        {"id": "cpu_tctl", "color": "#ff0000", "legend": "CPU Tctl"}
      ]
    },
    {
      "type": "custom",
      "script": "custom_graphs/nic_io.sh",
      "filename": "nic_io_day.png",
      "title": "Network IO — Day",
      "start": "-1d",
      "end": "now",
      "width": 1200,
      "height": 400
    },
    {
      "type": "custom",
      "script": "/config/custom_graphs/disk_temps_stacked.sh",
      "filename": "disk_temps_stacked_week.png",
      "title": "Disk Temperatures (Stacked) — Week",
      "start": "-7d",
      "end": "now",
      "width": 1200,
      "height": 400
    }
  ]
}
```

**Notes**:
- `"type": "custom"` triggers custom script execution
- `"script"` can be relative (to `/config`) or absolute path
- Standard fields (`filename`, `title`, `start`, `end`, `width`, `height`) are still used
- `"series"` field not required for custom graphs (script handles DEF/LINE statements)

---

### 5. Documentation Updates

**Add to README.md**:

#### Custom Graph Scripts

For complex graph types (stacked areas, inverted IO, mixed visualizations), use custom bash scripts instead of JSON definitions:

```json
{
  "type": "custom",
  "script": "custom_graphs/my_graph.sh",
  "filename": "output.png",
  "start": "-1d",
  "end": "now",
  "width": 1200,
  "height": 400
}
```

**Script Interface**:

Your custom script receives these positional arguments:
1. `$1` - RRD database path
2. `$2` - Output PNG path
3. `$3` - Start time (e.g., `-1d`)
4. `$4` - End time (e.g., `now`)
5. `$5` - Width in pixels
6. `$6` - Height in pixels
7. `$7` - Theme environment file path

**Using Themes**:

Source the theme env file to access colors and fonts:
```bash
. "$7"  # Source theme env file

# Use theme variables
rrdtool graph "$OUTPUT" \
  --color BACK"${THEME_COLOR_BACK}" \
  --color PRIMARY"${THEME_COLOR_PRIMARY}" \
  --font DEFAULT:"${THEME_FONT_DEFAULT}"
```

**Available theme variables**:
- Colors: `THEME_COLOR_BACK`, `THEME_COLOR_CANVAS`, `THEME_COLOR_PRIMARY`, etc.
- Fonts: `THEME_FONT_DEFAULT`, `THEME_FONT_TITLE`, `THEME_FONT_LEGEND`

**Example scripts**: See `examples/` directory for reference implementations.

---

## Implementation Checklist

- [ ] Create `scripts/theme_to_env.sh` helper script
- [ ] Modify `graph_config.py`:
  - [ ] Add `run_custom_graph()` function
  - [ ] Add `generate_theme_env()` helper
  - [ ] Add type detection in main loop
- [ ] Create example scripts:
  - [ ] `examples/nic_io.sh` - Network IO with inverted download
  - [ ] `examples/disk_temps_stacked.sh` - Stacked area graph
  - [ ] `examples/cpu_load_mixed.sh` - Mixed line + area
  - [ ] `examples/temps_with_thresholds.sh` - Graphs with HRULE warnings
- [ ] Update documentation:
  - [ ] Add custom graph section to README.md
  - [ ] Document script interface
  - [ ] Document theme variables
  - [ ] Add JSON config examples
- [ ] Testing:
  - [ ] Test standard graphs still work (backwards compatibility)
  - [ ] Test custom script with theme integration
  - [ ] Test relative and absolute script paths
  - [ ] Test error handling (missing script, script failures)

## Benefits

✅ **Backwards Compatible**: Existing JSON graphs continue to work unchanged
✅ **Simple Stays Simple**: Basic graphs remain in JSON (no bash required)
✅ **Complex When Needed**: Full RRDtool power via bash for advanced use cases
✅ **Theme Integration**: Custom scripts can use theme colors/fonts
✅ **User-Friendly**: Clear script interface with documented positional args
✅ **Flexible**: Users can place scripts anywhere, reference by path
✅ **Maintainable**: Clean separation between simple and complex graph types

## Future Enhancements

- Add script validation tool to check custom scripts before deployment
- Create gallery of community custom graph scripts
- Add script debugging mode with verbose output
- Support for script templates with variable substitution
