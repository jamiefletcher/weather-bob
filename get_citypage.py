import requests
import re
import os

BASE = "https://dd.weather.gc.ca/today/citypage_weather/ON/"
station = "s0000458"

pattern = rf'\d{{8}}T\d{{6}}\.\d+Z_MSC_CitypageWeather_{station}_en\.xml'

latest_file = None
latest_cycle = None

for cycle in range(23, -1, -1):
    url = f"{BASE}{cycle:02d}/"
    r = requests.get(url, timeout=10)

    matches = re.findall(pattern, r.text)

    if matches:
        latest_file = sorted(matches)[-1]
        latest_cycle = cycle
        break

if latest_file:
    download_url = f"{BASE}{latest_cycle:02d}/{latest_file}"

    os.makedirs("data/citypage", exist_ok=True)

    # 👇 fixed filename
    path = f"data/citypage/citypage_{station}_latest.xml"

    res = requests.get(download_url)

    with open(path, "wb") as f:
        f.write(res.content)
else:
    print("not found")