import os
import shutil
import subprocess
from urllib.request import urlopen
from datetime import datetime, timezone

# =========================
# CONFIG
# =========================
BASE_URL = "https://dd.weather.gc.ca/today/model_gdps/15km"
OUT_DIR = "data/gdps"
TILE_DIR = os.path.join(OUT_DIR, "tiles")
COLOR_MAP = "data/white-black.txt"

RUN = "12"

# =========================
# HELPERS
# =========================
def download_file(url, path):
    print(f"Downloading: {url}")
    with urlopen(url, timeout=30) as r, open(path, "wb") as f:
        shutil.copyfileobj(r, f)

def get_ref_time(grib_path):
    result = subprocess.run(
        ["gdalinfo", grib_path],
        capture_output=True,
        text=True
    )
    for line in result.stdout.splitlines():
        if "GRIB_REF_TIME=" in line:
            return int(line.split("=")[1].strip())
    return None

# =========================
# SETUP
# =========================
shutil.rmtree(OUT_DIR, ignore_errors=True)
os.makedirs(OUT_DIR, exist_ok=True)

# run selection (no validation check)
DATE = datetime.now(timezone.utc).strftime("%Y%m%d")

# =========================
# DOWNLOAD 000
# =========================
h = "000"

url = f"{BASE_URL}/{RUN}/{h}/{DATE}T{RUN}Z_MSC_GDPS_TotalCloudCover_Sfc_LatLon0.15_PT{h}H.grib2"
tmp_file = os.path.join(OUT_DIR, f"tmp_{h}.grib2")

download_file(url, tmp_file)

# =========================
# REF TIME
# =========================
ref_ts = get_ref_time(tmp_file)

dt = datetime.fromtimestamp(ref_ts, tz=timezone.utc)
utc_date = dt.strftime("%Y%m%d")
utc_hour = dt.strftime("%H")

first_file = os.path.join(OUT_DIR, f"utc_{utc_date}_{utc_hour}.grib2")
os.rename(tmp_file, first_file)

# =========================
# DOWNLOAD FORECAST HOURS
# =========================
for fh in range(1, 25):
    h = f"{fh:03d}"

    url = f"{BASE_URL}/{RUN}/{h}/{DATE}T{RUN}Z_MSC_GDPS_TotalCloudCover_Sfc_LatLon0.15_PT{h}H.grib2"

    valid_ts = ref_ts + fh * 3600
    dt = datetime.fromtimestamp(valid_ts, tz=timezone.utc)

    utc_date = dt.strftime("%Y%m%d")
    utc_hour = dt.strftime("%H")

    out_file = os.path.join(OUT_DIR, f"utc_{utc_date}_{utc_hour}.grib2")

    download_file(url, out_file)
    print(f"Saved: {out_file}")

# =========================
# TILE PHASE
# =========================
shutil.rmtree(TILE_DIR, ignore_errors=True)
os.makedirs(TILE_DIR, exist_ok=True)

target_ts = int(datetime.now(timezone.utc).timestamp())

best_file = None
best_diff = float("inf")

for fname in os.listdir(OUT_DIR):
    if not fname.startswith("utc_"):
        continue

    date_part = fname.split("_")[1]
    hour_part = fname.split("_")[2].split(".")[0]

    file_dt = datetime.strptime(
        f"{date_part} {hour_part}",
        "%Y%m%d %H"
    ).replace(tzinfo=timezone.utc)

    file_ts = int(file_dt.timestamp())
    diff = abs(target_ts - file_ts)

    if file_ts <= target_ts and diff < best_diff:
        best_diff = diff
        best_file = os.path.join(OUT_DIR, fname)

print(f"Using: {best_file}")

cmd = [
    "gdal", "raster", "pipeline",
    "read", best_file,
    "!", "color-map",
    "--color-map", COLOR_MAP,
    "--add-alpha",
    "--color-selection", "interpolate",
    "!", "reproject",
    "--dst-crs=EPSG:3857",
    "!", "tile", TILE_DIR,
    "--add-alpha",
    "--skip-blank",
    "--min-zoom", "0",
    "--max-zoom", "3",
    "--tile-size", "256"
]

subprocess.run(cmd, check=True)