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
: ${THEME_COLOR_FRAME:="#CCCCCC"}
: ${THEME_COLOR_AXIS:="#000000"}
: ${THEME_COLOR_GRID:="#E0E0E080"}
: ${THEME_COLOR_MGRID:="#C0C0C0B3"}
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
  --color FRAME"${THEME_COLOR_FRAME}" \
  --color AXIS"${THEME_COLOR_AXIS}" \
  --color GRID"${THEME_COLOR_GRID}" \
  --color MGRID"${THEME_COLOR_MGRID}" \
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
