#!/bin/sh
# Custom graph: Disk I/O Activity with inverted reads (Cacti-style)
#
# Positional arguments:
#   $1 = RRD_PATH       (e.g., /data/disk_io.rrd)
#   $2 = OUTPUT_PATH    (e.g., /data/graphs/disk_io_io_day.png)
#   $3 = START          (e.g., -1d)
#   $4 = END            (e.g., now)
#   $5 = WIDTH          (e.g., 1200)
#   $6 = HEIGHT         (e.g., 400)
#   $7 = THEME_ENV_FILE (e.g., /tmp/theme_disk_io.env)

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
: ${THEME_COLOR_BACK:="#0F1115"}
: ${THEME_COLOR_CANVAS:="#0B0E14"}
: ${THEME_COLOR_FONT:="#E6E8EB"}
: ${THEME_COLOR_FRAME:="#2A2F3A"}
: ${THEME_COLOR_AXIS:="#A6ADB7"}
: ${THEME_COLOR_GRID:="#3A404880"}
: ${THEME_COLOR_MGRID:="#545B66B3"}
: ${THEME_COLOR_PRIMARY:="#FF6A00"}
: ${THEME_COLOR_AMBER:="#FFB100"}
: ${THEME_COLOR_ACCENT:="#3B82F6"}
: ${THEME_FONT_DEFAULT:="11"}
: ${THEME_FONT_TITLE:="13"}

# Build rrdtool graph command with inverted reads and stacked writes
rrdtool graph "$OUTPUT" \
  --start "$START" --end "$END" \
  --width "$WIDTH" --height "$HEIGHT" \
  --title "Disk I/O Activity" \
  --vertical-label "ops/sec" \
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
  --alt-autoscale \
  DEF:disk1_reads="$RRD_PATH:disk1_reads:AVERAGE" \
  DEF:disk1_writes="$RRD_PATH:disk1_writes:AVERAGE" \
  DEF:disk2_reads="$RRD_PATH:disk2_reads:AVERAGE" \
  DEF:disk2_writes="$RRD_PATH:disk2_writes:AVERAGE" \
  DEF:parity_reads="$RRD_PATH:parity_reads:AVERAGE" \
  DEF:parity_writes="$RRD_PATH:parity_writes:AVERAGE" \
  DEF:cache_reads="$RRD_PATH:cache_reads:AVERAGE" \
  DEF:cache_writes="$RRD_PATH:cache_writes:AVERAGE" \
  CDEF:disk1_reads_neg=disk1_reads,-1,* \
  CDEF:disk2_reads_neg=disk2_reads,-1,* \
  CDEF:parity_reads_neg=parity_reads,-1,* \
  CDEF:cache_reads_neg=cache_reads,-1,* \
  AREA:disk1_writes"${THEME_COLOR_PRIMARY}80":"Disk 1 Writes" \
  AREA:disk2_writes"${THEME_COLOR_AMBER}80":"Disk 2 Writes":STACK \
  AREA:cache_writes"${THEME_COLOR_GREEN}80":"Cache Writes":STACK \
  AREA:parity_writes"${THEME_COLOR_ACCENT}80":"Parity Writes":STACK \
  AREA:disk1_reads_neg"${THEME_COLOR_PRIMARY}":"Disk 1 Reads" \
  AREA:disk2_reads_neg"${THEME_COLOR_AMBER}":"Disk 2 Reads":STACK \
  AREA:cache_reads_neg"${THEME_COLOR_GREEN}":"Cache Reads":STACK \
  AREA:parity_reads_neg"${THEME_COLOR_ACCENT}":"Parity Reads":STACK \
  HRULE:0"${THEME_COLOR_FONT}":""

echo "Generated: $OUTPUT"
