import json
import xml.etree.ElementTree as ET
from urllib.request import urlopen

url = "https://aviationweather.gov/data/cache/metars.cache.xml"
path = "data/metars/metars.cache.xml"

with urlopen(url, timeout=30) as response:
    data = response.read()

with open(path, "wb") as f:
    f.write(data)

# -------------------------
# LOAD AIRPORTS (index)
# -------------------------
with open("data/airports.geojson") as f:
    airports = json.load(f)["features"]

airport_map = {
    a["properties"]["icao_code"]: a["properties"]
    for a in airports
    if a.get("properties", {}).get("icao_code")
}

# -------------------------
# STREAM METARS XML
# -------------------------
joined = []

context = ET.iterparse("data/metars/metars.cache.xml", events=("end",))
_, root = next(context)

for event, elem in context:
    if elem.tag != "METAR":
        continue

    station_id = elem.findtext("station_id")
    temp_c = elem.findtext("temp_c")
    lon = elem.findtext("longitude")
    lat = elem.findtext("latitude")

    # -------------------------
    # VALIDATION
    # -------------------------
    if not station_id:
        elem.clear()
        root.clear()
        continue

    airport = airport_map.get(station_id)
    if not airport:
        elem.clear()
        root.clear()
        continue

    municipality = airport.get("municipality")
    if not municipality or temp_c is None:
        elem.clear()
        root.clear()
        continue

    try:
        temp_c = float(temp_c)
    except (TypeError, ValueError):
        elem.clear()
        root.clear()
        continue

    if temp_c < -80 or temp_c > 60:
        elem.clear()
        root.clear()
        continue

    # -------------------------
    # COORDINATES
    # -------------------------
    if lon is None or lat is None:
        elem.clear()
        root.clear()
        continue

    try:
        lon = float(lon)
        lat = float(lat)
    except (TypeError, ValueError):
        elem.clear()
        root.clear()
        continue

    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        elem.clear()
        root.clear()
        continue

    # -------------------------
    # WX STRING (raw, JS decodes it)
    # -------------------------
    wx_string = elem.findtext("wx_string")

    # -------------------------
    # SKY CONDITIONS (multi-layer)
    # -------------------------
    sky_conditions = []

    for sc in elem.findall("sky_condition"):
        sky_conditions.append({
            "sky_cover": sc.get("sky_cover"),
            "cloud_base_ft_agl": sc.get("cloud_base_ft_agl")
        })

    # sort by altitude (important for JS "top layer" logic)
    sky_conditions.sort(
        key=lambda x: int(x["cloud_base_ft_agl"] or 999999)
    )

    # -------------------------
    # BUILD FEATURE
    # -------------------------
    joined.append({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat]
        },
        "properties": {
            "station_id": station_id,
            "temp_c": temp_c,

            "icao_code": airport.get("icao_code"),
            "municipality": municipality,
            "iso_country": airport.get("iso_country"),
            "iso_region": airport.get("iso_region"),

            # RAW DATA (your JS decodes everything)
            "wx_string": wx_string,
            "sky_condition": sky_conditions
        }
    })

    elem.clear()
    root.clear()

# -------------------------
# WRITE OUTPUT
# -------------------------
with open("data/metars/metars_airports.geojson", "w") as f:
    json.dump(
        {"type": "FeatureCollection", "features": joined},
        f
    )