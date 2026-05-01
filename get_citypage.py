import requests
import re

BASE = "https://dd.weather.gc.ca/today/citypage_weather/ON/"
station = "s0000458"

pattern = rf'\d{{8}}T\d{{6}}\.\d+Z_MSC_CitypageWeather_{station}_en\.xml'

for cycle in range(23, -1, -1):
    r = requests.get(f"{BASE}{cycle:02d}/", timeout=10)

    matches = re.findall(pattern, r.text)
    if matches:
        print(sorted(matches)[-1])  # latest by timestamp
        break