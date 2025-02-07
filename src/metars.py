import os
import json
import urllib.parse
import openai
import requests

# def download_metars(save_folder, url="https://aviationweather.gov/data/cache/metars.cache.xml"):
#     print("Downloading new METARS data from", url)
#     resp = requests.get(url)
#     if resp.status_code == 200:
#         filename = os.path.basename(url)
#         with open(f"{save_folder}/{filename}", "w") as metars_file:
#             metars_file.write(resp.text)
#     else:
#         print("Error downloading METARS", resp.status_code)

STATION_IDS = ["CYYZ", "OMDB", "LTFM", "KLAX", "WIII"]
WEATHER_PARAMS = {
    "site": "station_name",
    "obsTime": "time_utc",
    "temp": "temperature_c",
    "dewp": "dew_point_c",
    "wspd": "wind_speed_kt",
    "wdir": "wind_direction",
    "wgst": "wind_gust_kt",
    "cover": "cloud_cover",
    "wx": "wx_code",
}
INSTRUCTIONS = (
    "You are an AI assistant specialized in interpreting and describing weather data stored in JSON format. "
    "You are expert at reading weather data for a given location and providing an English description of the weather at that location. "
    "The English weather description should be in the style of TV weatherman."
)
PROMPT = (
    "Briefly describe the weather for the location identified in the following JSON data. "
    "Format your response as a JSON object with the following key: 'weather_description'. "
)


def process_metars(raw_metars, properties):
    stations = {}
    for weather_report in raw_metars:
        station = {}

        station_id = weather_report["properties"].get("id")
        if station_id not in stations:
            stations[station_id] = station

        for property, feat_name in properties.items():
            station[feat_name] = weather_report["properties"].get(property, None)

        station["geometry"] = weather_report.get("geometry", None)

        stations[station_id].update(station)
    return stations


def download_metars(args, properties, base_url="https://aviationweather.gov/api/data/metar"):
    params = urllib.parse.urlencode(args)
    url = f"{base_url}?{params}"
    print("Downloading new METARS data from", url)

    resp = requests.get(url)
    if resp.status_code != 200:
        print("Error downloading METARS", resp.status_code)
        return None
    metars_json = json.loads(resp.text)
    metars = process_metars(metars_json["features"], properties)
    return metars


def main():
    args = {"ids": ",".join(STATION_IDS), "format": "geojson", "taf": False, "hours": 1}
    metars = download_metars(args, WEATHER_PARAMS)
    with open("data/metars/current-weather.json", "w") as f:
        json.dump(metars, f, indent=4)

if __name__ == "__main__":
    main()
