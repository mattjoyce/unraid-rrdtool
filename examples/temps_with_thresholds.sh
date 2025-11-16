#!/bin/sh
# Custom graph: Temperature monitoring with warning threshold lines
#
# Positional arguments:
#   $1 = RRD_PATH       (e.g., /data/system.rrd)
#   $2 = OUTPUT_PATH    (e.g., /data/graphs/system_temps_thresholds_day.png)
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
: ${THEME_COLOR_PRIMARY:="#FF6A00"}
: ${THEME_COLOR_ACCENT:="#3B82F6"}
: ${THEME_COLOR_WARN_HRULE:="#FFD166CC"}
: ${THEME_COLOR_CRITICAL_HRULE:="#FF4D00CC"}
: ${THEME_FONT_DEFAULT:="11"}
: ${THEME_FONT_TITLE:="13"}

# Build graph with warning and critical threshold lines
# NOTE: Adjust sensor IDs (cpu_temp, sys_temp) to match your RRD data sources
rrdtool graph "$OUTPUT" \
  --start "$START" --end "$END" \
  --width "$WIDTH" --height "$HEIGHT" \
  --title "System Temperatures with Thresholds" \
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
  --upper-limit 100 \
  DEF:cpu_temp="$RRD_PATH:cpu_temp:AVERAGE" \
  DEF:sys_temp="$RRD_PATH:sys_temp:AVERAGE" \
  LINE2:cpu_temp"${THEME_COLOR_PRIMARY}":"CPU Temperature" \
  GPRINT:cpu_temp:LAST:"Current\:%5.1lf°C" \
  GPRINT:cpu_temp:AVERAGE:"Avg\:%5.1lf°C" \
  GPRINT:cpu_temp:MAX:"Max\:%5.1lf°C\n" \
  LINE2:sys_temp"${THEME_COLOR_ACCENT}":"System Temperature" \
  GPRINT:sys_temp:LAST:"Current\:%5.1lf°C" \
  GPRINT:sys_temp:AVERAGE:"Avg\:%5.1lf°C" \
  GPRINT:sys_temp:MAX:"Max\:%5.1lf°C\n" \
  HRULE:70"${THEME_COLOR_WARN_HRULE}":"Warning Threshold (70°C)\n" \
  HRULE:85"${THEME_COLOR_CRITICAL_HRULE}":"Critical Threshold (85°C)"

echo "Generated: $OUTPUT"
