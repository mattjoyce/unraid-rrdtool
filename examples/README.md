# Custom Graph Script Examples

This directory contains example bash scripts that demonstrate advanced RRDtool graphing capabilities beyond what's practical to express in JSON configuration.

## Available Examples

### `nic_io.sh` - Network IO with Inverted Download (Cacti-style)

Creates a dual-area graph showing network traffic with downloads inverted below the zero line and uploads above, similar to Cacti network monitoring graphs.

**Features:**
- AREA graphs for visual impact
- CDEF to negate download values for bottom-half display
- HRULE at zero for visual reference
- GPRINT statements for current/avg/max statistics

**Required RRD data sources:**
- `eth0_rx_bytes` - Received bytes (COUNTER or DERIVE type)
- `eth0_tx_bytes` - Transmitted bytes (COUNTER or DERIVE type)

### `disk_temps_stacked.sh` - Stacked Area Graph for Multiple Disks

Creates a stacked area chart showing multiple disk temperatures layered on top of each other, useful for visualizing total thermal load.

**Features:**
- Stacked AREA graphs using `:STACK` modifier
- Individual GPRINT statistics per disk
- Warning threshold HRULE at 50°C

**Required RRD data sources:**
- `disk1_temp`, `disk2_temp`, `disk3_temp`, `disk4_temp` (GAUGE type)

### `temps_with_thresholds.sh` - Temperature Graphs with Warning Thresholds

Creates a temperature monitoring graph with horizontal reference lines marking warning and critical thresholds.

**Features:**
- LINE2 graphs for clear visibility
- Multiple HRULE statements for warning (70°C) and critical (85°C) thresholds
- Semi-transparent threshold lines using alpha channel

**Required RRD data sources:**
- `cpu_temp` - CPU temperature (GAUGE type)
- `sys_temp` - System temperature (GAUGE type)

## How to Use

1. **Copy to your config directory:**
   ```bash
   mkdir -p config/custom_graphs
   cp examples/*.sh config/custom_graphs/
   chmod +x config/custom_graphs/*.sh
   ```

2. **Edit scripts to match your RRD data sources:**
   - Open the script in a text editor
   - Find the `DEF:` statements
   - Change the data source names (e.g., `disk1_temp`, `eth0_rx_bytes`) to match your actual RRD DS names
   - You can check your RRD DS names with: `rrdtool info /data/your_database.rrd | grep "^ds\["`

3. **Reference in your config JSON:**
   ```json
   {
     "graphs": [
       {
         "type": "custom",
         "script": "custom_graphs/nic_io.sh",
         "filename": "nic_io_day.png",
         "start": "-1d",
         "width": 1200,
         "height": 400
       }
     ]
   }
   ```

## Script Interface

All custom graph scripts receive these positional arguments:

| Argument | Description | Example |
|----------|-------------|---------|
| `$1` | RRD database path | `/data/system.rrd` |
| `$2` | Output PNG path | `/data/graphs/system_custom_day.png` |
| `$3` | Start time | `-1d` |
| `$4` | End time | `now` |
| `$5` | Width in pixels | `1200` |
| `$6` | Height in pixels | `400` |
| `$7` | Theme environment file | `/tmp/theme_system.env` |

## Theme Integration

Custom scripts can source the theme environment file (argument `$7`) to access theme colors and fonts:

```bash
THEME_ENV="$7"
if [ -f "$THEME_ENV" ]; then
    . "$THEME_ENV"
fi

# Now you can use theme variables
rrdtool graph "$OUTPUT" \
  --color BACK"${THEME_COLOR_BACK}" \
  --color PRIMARY"${THEME_COLOR_PRIMARY}"
```

Available theme variables:
- **Scaffolding**: `THEME_COLOR_BACK`, `THEME_COLOR_CANVAS`, `THEME_COLOR_FRAME`, `THEME_COLOR_FONT`, `THEME_COLOR_AXIS`, `THEME_COLOR_GRID`, `THEME_COLOR_MGRID`, `THEME_COLOR_ARROW`
- **Series**: `THEME_COLOR_PRIMARY`, `THEME_COLOR_AMBER`, `THEME_COLOR_GREEN`, `THEME_COLOR_RED`, `THEME_COLOR_ACCENT`
- **Alarms**: `THEME_COLOR_WARN_HRULE`, `THEME_COLOR_CRITICAL_HRULE`
- **Fonts**: `THEME_FONT_DEFAULT`, `THEME_FONT_TITLE`, `THEME_FONT_AXIS`, `THEME_FONT_LEGEND`

## Creating Your Own Custom Graphs

1. Start with one of the example scripts as a template
2. Modify the RRD data source names to match your data
3. Customize the graph title, vertical label, and legend text
4. Adjust colors, thresholds, and visual styling as needed
5. Test the script manually before adding to config:
   ```bash
   ./custom_graphs/my_script.sh /data/system.rrd /tmp/test.png -1d now 1200 400 /tmp/empty.env
   ```

## RRDtool Documentation

For advanced graph customization, refer to the official RRDtool documentation:
- [rrdgraph](https://oss.oetiker.ch/rrdtool/doc/rrdgraph.en.html) - Graph creation
- [rrdgraph_graph](https://oss.oetiker.ch/rrdtool/doc/rrdgraph_graph.en.html) - Graph elements (LINE, AREA, STACK, etc.)
- [rrdgraph_data](https://oss.oetiker.ch/rrdtool/doc/rrdgraph_data.en.html) - DEF and CDEF definitions
- [CDEF Tutorial](https://oss.oetiker.ch/rrdtool/tut/cdeftutorial.en.html) - Complex data expressions
