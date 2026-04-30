import requests

BASE = "https://dd.weather.gc.ca/today/citypage_weather/ON/"
TARGET = "_s0000458_en.xml"

for cycle in range(23, -1, -1):
    r = requests.get(f"{BASE}{cycle}/", timeout=10)
    if TARGET in r.text:
        # extract filename directly from text
        for part in r.text.split():
            if TARGET in part:
                print(part.split('"')[1])
                exit()