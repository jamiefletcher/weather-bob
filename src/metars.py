import json
import math
import urllib.parse
import openai
import requests


INSTRUCTIONS = (
    "You are a weather expert specialized in interpreting and describing weather data stored in JSON format. "
    "You read weather data for a given location and providing an English description of the weather at that location. "
    "The English weather description should be no more than 200 words and in the style of TV weatherman. "
    "Use common short forms for units. For example, '°C' for degrees Celcius and 'km/h' for kilometers per hour. "
    "Emphasize each number in the description by enclosing the number and its unit within HTML bold tags. For example, <b>23.1 km/h</b> "
)
PROMPT = (
    "Briefly describe the weather for the location identified in the following JSON data. "
    "Format your response as a JSON object with the following key: 'weather_description'. "
)


class Metars:
    base_url = "https://aviationweather.gov/api/data/metar"

    def _relative_humidity(temperature, dewpoint, decimals=1):
        # https://en.wikipedia.org/wiki/Clausius%E2%80%93Clapeyron_relation#Meteorology_and_climatology
        pp = math.exp((17.625 * dewpoint) / (243.04 + dewpoint))
        svp = math.exp((17.625 * temperature) / (243.04 + temperature))
        return round(100 * pp / svp, decimals)

    def _kts_to_kmph(speed, decimals=1):
        return round(speed * 1.852, decimals)

    def _decode_wx(
        wx,
        precip={
            "VC": "In the vicinity",
            "MI": "Shallow",
            "PR": "Partial",
            "BC": "Patches",
            "DR": "Low drifting",
            "BL": "Blowing",
            "SH": "Showers",
            "TS": "Thunderstorm",
            "FZ": "Freezing",
            "RA": "Rain",
            "DZ": "Drizzle",
            "SN": "Snow",
            "SG": "Snow Grains",
            "IC": "Ice Crystals",
            "PL": "Ice Pellets",
            "GR": "Hail",
            "GS": "Graupel",
            "UP": "Precipitation",
            "FG": "Fog",
            "VA": "Volcanic Ash",
            "BR": "Mist",
            "HZ": "Haze",
            "DU": "Widespread Dust",
            "FU": "Smoke",
            "SA": "Sand",
            "PY": "Spray",
            "SQ": "Squall",
            "PO": "Dust",
            "DS": "Duststorm",
            "SS": "Sandstorm",
            "FC": "Funnel Cloud",
        },
    ):
        description = ""
        for wx_code in wx.split(" "):
            if wx_code[0] == "-":
                description += "Light "
                wx_code = wx_code[1:]
            elif wx_code[0] == "+":
                description += "Heavy "
                wx_code = wx_code[1:]
            elif wx_code[:2] == "VC":
                wx_code = wx_code[2:] + "VC"
            else:
                description += "Moderate "
            while len(wx_code) > 1:
                code = wx_code[:2]
                wx_code = wx_code[2:]
                description += f"{precip[code]} "
        return description.lower()[:-1]

    def __init__(
        self, station_id: str, place_name: str, utc_offset: int, geometry: dict
    ):
        self.station_id = station_id
        self.place_name = place_name
        self.utc_offset = utc_offset
        self.geometry = geometry
        self.request_args = {
            "ids": station_id,
            "format": "geojson",
            "taf": False,
            "hours": 2,
        }

    def download(self):
        params = urllib.parse.urlencode(self.request_args)
        url = f"{Metars.base_url}?{params}"
        print("  Downloading new METARS data from", url)

        resp = requests.get(url)
        if resp.status_code != 200:
            print("  Error downloading METARS", resp.status_code)
            return
        metars_json = json.loads(resp.text)
        self.weather = metars_json["features"][0]["properties"]
        self._add_weather_fields()

    def weather_report(
        self, client: openai.OpenAI, model: str, sys_prompt: str, prompt: str
    ):
        print(f"  Generating weather report for {self.station_id}")
        weather = self._weather_summary_for_llm()
        msgs = [{"role": "system", "content": sys_prompt}]
        content = [
            {
                "type": "text",
                "text": f"{prompt} \n\nWEATHER DATA: {json.dumps(weather)}",
            }
        ]
        msgs.append({"role": "user", "content": content})
        response = gpt_chat(client=client, model=model, messages=msgs)
        self.weather.update(json.loads(response))

    def _weather_summary_for_llm(
        self,
        summary_params={
            "temperature_c": "temp",
            "relative_humidity": "rh",
            "wind_speed_kmph": "wspd_kmph",
            "wind_gust_kmph": "wgst_kmph",
            "observed_weather": "wx_descrip",
        },
    ):
        summary = {"place_name": self.place_name}
        for long_name, short_name in summary_params.items():
            if short_name in self.weather:
                summary.update({long_name: self.weather[short_name]})
        return summary

    def _add_weather_fields(self):
        self.weather["place_name"] = self.place_name
        self.weather["geometry"] = self.geometry
        # time_utc = self.weather.get("obsTime")  # TODO: Convert to local

        wx = self.weather.get("wx", None)
        if wx:
            print(wx)
            self.weather["wx_descrip"] = Metars._decode_wx(wx)

        wspd = self.weather.get("wspd", None)
        if wspd:
            self.weather["wspd_kmph"] = Metars._kts_to_kmph(wspd)

        wgst = self.weather.get("wgst", None)
        if wgst:
            self.weather["wgst_kmph"] = Metars._kts_to_kmph(wgst)

        t = self.weather.get("temp", None)
        dt = self.weather.get("dewp", None)
        if t and dt:
            self.weather["rh"] = Metars._relative_humidity(t, dt)


def gpt_list_models(client):
    for m in client.models.list():
        print(m.id)


def gpt_chat(client: openai.OpenAI, model: str, messages: list, max_tokens=1024):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
    )
    weather_report = ""
    if response.choices[0].finish_reason == "stop":
        weather_report = response.choices[0].message.content
    return weather_report


def main():
    openai_client = openai.OpenAI()
    metars = []
    output_data = {}

    with open("data/metars/metars-places.geojson", "r") as places_file:
        places = json.load(places_file)
        for feat in places["features"]:
            metars.append(
                Metars(
                    station_id=feat["properties"]["station_id"],
                    place_name=feat["properties"]["place"],
                    utc_offset=int(feat["properties"]["utc_offset"]),
                    geometry=feat["geometry"],
                )
            )

    for m in metars:
        print(m.station_id)
        m.download()
        m.weather_report(
            openai_client, model="gpt-4o-mini", sys_prompt=INSTRUCTIONS, prompt=PROMPT
        )
        output_data[m.station_id] = m.weather

    with open("data/metars/current-weather.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
