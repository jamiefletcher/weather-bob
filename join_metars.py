import json
import xml.etree.ElementTree as ET

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
# STREAM METARS XML (memory-safe)
# -------------------------
joined = []

context = ET.iterparse("data/metars/metars.cache.xml", events=("end",))
_, root = next(context)  # important: get root for clearing

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
            "iso_region": airport.get("iso_region")
        }
    })

    # IMPORTANT: free memory
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