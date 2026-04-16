#!/bin/bash

### CONFIG
RUN="00"
DATE=$(date +%Y%m%d)  # Current date
BASE_URL="https://dd.weather.gc.ca/today/model_gdps/15km"
OUT_DIR="data/gdps"

# Remove existing directory and recreate
rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"

### FUNCTIONS
download_file() {
    local url="$1"
    local path="$2"
    if [[ -f "$path" ]]; then
        # File exists, skip
        return 0
    fi
    echo "Downloading: $url"
    # Use curl with -f to fail silently on 404s, -L to follow redirects, -o to specify output file
    curl -f -L -o "$path" "$url"
    # Check if curl was successful (exit code 0)
    if [[ $? -eq 0 ]]; then
        return 0
    else
        # Optionally print an error message if download failed
        # echo "Failed to download: $url"
        return 1
    fi
}

for h in $(seq -f "%03g" 0 1 24); do  # Loop from 3 to 240, incrementing by 3, format as 0-padded 3-digit
    grib_file="${OUT_DIR}/${h}.grib2"
    # Construct URL inside the loop
    url="${BASE_URL}/${RUN}/${h}/${DATE}T${RUN}Z_MSC_GDPS_TotalCloudCover_Sfc_LatLon0.15_PT${h}H.grib2"
    download_file "$url" "$grib_file"
done