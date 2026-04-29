import json
import xml.etree.ElementTree as ET
from urllib.request import urlopen

# -------------------------
# DOWNLOAD METAR CACHE
# -------------------------
url = "https://aviationweather.gov/data/cache/metars.cache.xml"
path = "data/metars/metars.cache.xml"

with urlopen(url, timeout=30) as response:
    with open(path, "wb") as f:
        f.write(response.read())

# -------------------------
# LOAD PLACES
# -------------------------
with open("data/places_airports.geojson") as f:
    places = json.load(f)["features"]

places_map = {
    f["properties"]["icao_code"]: f
    for f in places
    if f.get("properties", {}).get("icao_code")
}

# -------------------------
# STREAM METARS XML
# -------------------------
joined = []

context = ET.iterparse(path, events=("end",))
_, root = next(context)

for _, elem in context:
    if elem.tag != "METAR":
        continue

    station_id = (elem.findtext("station_id") or "").strip().upper()
    place_feature = places_map.get(station_id)

    if not place_feature:
        elem.clear()
        continue

    lon, lat = place_feature["geometry"]["coordinates"]

    # -------------------------
    # FULL METAR FIELD DUMP
    # -------------------------
    metar_fields = {}

    for child in elem:
        # skip structured repeats handled separately
        if child.tag == "sky_condition":
            continue

        if child.text is not None:
            metar_fields[child.tag] = child.text

    # -------------------------
    # REQUIRED FIELDS (cleaned)
    # -------------------------
    temp_c = metar_fields.get("temp_c")
    if temp_c is None:
        elem.clear()
        continue

    wx_string = metar_fields.get("wx_string")

    # -------------------------
    # SKY CONDITIONS (structured)
    # -------------------------
    sky_conditions = [
        {
            "sky_cover": sc.get("sky_cover"),
            "cloud_base_ft_agl": sc.get("cloud_base_ft_agl")
        }
        for sc in elem.findall("sky_condition")
    ]

    def safe_alt(x):
        try:
            return int(x["cloud_base_ft_agl"] or 999999)
        except:
            return 999999

    sky_conditions.sort(key=safe_alt)

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
            **place_feature["properties"],

            # FULL METAR RAW FIELDS
            **metar_fields,

            # OVERRIDES / NORMALIZED FIELDS
            "temp_c": float(temp_c),
            "wx_string": wx_string,
            "sky_condition": sky_conditions
        }
    })

    elem.clear()

# -------------------------
# FINAL GEOJSON WRAPPER
# -------------------------
geojson = {
    "type": "FeatureCollection",
    "name": "metars_places_airports",
    "crs": {
        "type": "name",
        "properties": {
            "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
        }
    },
    "features": joined
}

with open("data/metars/metars_places_airports.geojson", "w") as f:
    json.dump(geojson, f)