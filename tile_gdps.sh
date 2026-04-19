#!/bin/bash

rm -rf data/gdps/tiles/*

TARGET_TS=$(date -u +%s)

BEST_FILE=""
BEST_DIFF=999999999

for f in data/gdps/utc_*.grib2; do

    # Extract YYYYMMDD and HH from filename
    BASENAME=$(basename "$f")
    DATE_PART=$(echo "$BASENAME" | cut -d'_' -f2)
    HOUR_PART=$(echo "$BASENAME" | cut -d'_' -f3 | cut -d'.' -f1)

    # Convert to epoch
    FILE_TS=$(date -u -d "${DATE_PART} ${HOUR_PART}:00 UTC" +%s)

    # Absolute difference
    DIFF=$(( TARGET_TS > FILE_TS ? TARGET_TS - FILE_TS : FILE_TS - TARGET_TS ))

    if [ $FILE_TS -le $TARGET_TS ] && [ $DIFF -lt $BEST_DIFF ]; then
        BEST_DIFF=$DIFF
        BEST_FILE=$f
    fi

done

echo "Using: $BEST_FILE"

gdal raster pipeline read "$BEST_FILE" \
    ! color-map --color-map 'data/white-black.txt' --add-alpha --color-selection interpolate \
    ! reproject --dst-crs='EPSG:3857' \
    ! tile data/gdps/tiles/ \
        --add-alpha --skip-blank --min-zoom 0 --max-zoom 3 --tile-size 256