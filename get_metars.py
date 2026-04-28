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
# LOAD AIRPORTS (index)
# -------------------------
with open("data/airports.geojson") as f:
    airports = json.load(f)["features"]

airport_map = {
    a["properties"]["icao_code"]: a["properties"]
    for a in airports
    if "icao_code" in a.get("properties", {})
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

    station_id = elem.findtext("station_id")
    airport = airport_map.get(station_id)

    if not airport:
        elem.clear()
        continue

    lon = elem.findtext("longitude")
    lat = elem.findtext("latitude")
    temp_c = elem.findtext("temp_c")

    if lon is None or lat is None or temp_c is None:
        elem.clear()
        continue

    lon = float(lon)
    lat = float(lat)
    temp_c = float(temp_c)

    wx_string = elem.findtext("wx_string")

    sky_conditions = [
        {
            "sky_cover": sc.get("sky_cover"),
            "cloud_base_ft_agl": sc.get("cloud_base_ft_agl")
        }
        for sc in elem.findall("sky_condition")
    ]

    sky_conditions.sort(
        key=lambda x: int(x["cloud_base_ft_agl"] or 999999)
    )

    joined.append({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat]
        },
        "properties": {
            # METAR
            "station_id": station_id,
            "temp_c": temp_c,
            "wx_string": wx_string,
            "sky_condition": sky_conditions,

            # AIRPORT (STRICT PASS-THROUGH)
            **airport
        }
    })

    elem.clear()

# -------------------------
# WRITE OUTPUT
# -------------------------
with open("data/metars/metars_airports.geojson", "w") as f:
    json.dump(
        {"type": "FeatureCollection", "features": joined},
        f
    )