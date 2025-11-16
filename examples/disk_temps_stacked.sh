#!/bin/sh
# Custom graph: Stacked area graph for multiple disk temperatures
#
# Positional arguments:
#   $1 = RRD_PATH       (e.g., /data/disks.rrd)
#   $2 = OUTPUT_PATH    (e.g., /data/graphs/disks_temps_stacked_day.png)
#   $3 = START          (e.g., -1d)
#   $4 = END            (e.g., now)
#   $5 = WIDTH          (e.g., 1200)
#   $6 = HEIGHT         (e.g., 400)
#   $7 = THEME_ENV_FILE (e.g., /tmp/theme_disks.env)

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
: ${THEME_COLOR_PRIMARY:="#FF6A00"}
: ${THEME_COLOR_AMBER:="#FFB100"}
: ${THEME_COLOR_GREEN:="#10B981"}
: ${THEME_COLOR_ACCENT:="#3B82F6"}
: ${THEME_FONT_DEFAULT:="11"}
: ${THEME_FONT_TITLE:="13"}

# Build stacked area graph for disk temperatures
# NOTE: Adjust disk sensor IDs (disk1_temp, disk2_temp, etc.) to match your RRD data sources
rrdtool graph "$OUTPUT" \
  --start "$START" --end "$END" \
  --width "$WIDTH" --height "$HEIGHT" \
  --title "Disk Temperatures (Stacked)" \
  --vertical-label "°C" \
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
  --upper-limit 60 \
  --rigid \
  DEF:disk1="$RRD_PATH:disk1_temp:AVERAGE" \
  DEF:disk2="$RRD_PATH:disk2_temp:AVERAGE" \
  DEF:disk3="$RRD_PATH:disk3_temp:AVERAGE" \
  DEF:disk4="$RRD_PATH:disk4_temp:AVERAGE" \
  AREA:disk1"${THEME_COLOR_PRIMARY}":"Disk 1":STACK \
  GPRINT:disk1:LAST:"Current\:%5.1lf°C" \
  GPRINT:disk1:AVERAGE:"Avg\:%5.1lf°C" \
  GPRINT:disk1:MAX:"Max\:%5.1lf°C\n" \
  AREA:disk2"${THEME_COLOR_AMBER}":"Disk 2":STACK \
  GPRINT:disk2:LAST:"Current\:%5.1lf°C" \
  GPRINT:disk2:AVERAGE:"Avg\:%5.1lf°C" \
  GPRINT:disk2:MAX:"Max\:%5.1lf°C\n" \
  AREA:disk3"${THEME_COLOR_GREEN}":"Disk 3":STACK \
  GPRINT:disk3:LAST:"Current\:%5.1lf°C" \
  GPRINT:disk3:AVERAGE:"Avg\:%5.1lf°C" \
  GPRINT:disk3:MAX:"Max\:%5.1lf°C\n" \
  AREA:disk4"${THEME_COLOR_ACCENT}":"Disk 4":STACK \
  GPRINT:disk4:LAST:"Current\:%5.1lf°C" \
  GPRINT:disk4:AVERAGE:"Avg\:%5.1lf°C" \
  GPRINT:disk4:MAX:"Max\:%5.1lf°C\n" \
  HRULE:50"#FF0000CC":"Warning Threshold (50°C)"

echo "Generated: $OUTPUT"
