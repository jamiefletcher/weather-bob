#!/bin/bash

### CONFIG
RUN="12"

BASE_CHECK="https://dd.weather.gc.ca/today/model_gdps/15km/${RUN}"

if ! curl -s --head "$BASE_CHECK" | head -n 1 | grep -q "200"; then
    echo "RUN 12 not available, falling back to 00"
    RUN="00"
fi

DATE=$(date -u +%Y%m%d)
BASE_URL="https://dd.weather.gc.ca/today/model_gdps/15km"
OUT_DIR="data/gdps"

rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"

download_file() {
    local url="$1"
    local path="$2"

    echo "Downloading: $url"
    curl -f -L -o "$path" "$url"
}

# --- download 000 first ---
h="000"
url="${BASE_URL}/${RUN}/${h}/${DATE}T${RUN}Z_MSC_GDPS_TotalCloudCover_Sfc_LatLon0.15_PT${h}H.grib2"
tmp_file="${OUT_DIR}/tmp_${h}.grib2"

download_file "$url" "$tmp_file" || exit 1

# --- extract reference time once ---
REF_TS=$(gdalinfo "$tmp_file" | awk -F= '/GRIB_REF_TIME/ {print $2}' | tr -d ' ')

if [[ -z "$REF_TS" ]]; then
    echo "Failed to read GRIB_REF_TIME"
    exit 1
fi

# process 000
VALID_TS=$REF_TS
UTC_DATE=$(date -u -d "@$VALID_TS" +%Y%m%d)
UTC_HOUR=$(date -u -d "@$VALID_TS" +%H)
mv "$tmp_file" "${OUT_DIR}/utc_${UTC_DATE}_${UTC_HOUR}.grib2"

# --- loop remaining hours ---
for h in $(seq -f "%03g" 1 1 24); do

    url="${BASE_URL}/${RUN}/${h}/${DATE}T${RUN}Z_MSC_GDPS_TotalCloudCover_Sfc_LatLon0.15_PT${h}H.grib2"

    FH=$((10#$h))

    VALID_TS=$((REF_TS + FH * 3600))

    UTC_DATE=$(date -u -d "@$VALID_TS" +%Y%m%d)
    UTC_HOUR=$(date -u -d "@$VALID_TS" +%H)

    final_file="${OUT_DIR}/utc_${UTC_DATE}_${UTC_HOUR}.grib2"

    download_file "$url" "$final_file" || continue

    echo "Saved: $final_file"

done