import json
import math
import urllib.parse
import openai
import requests


STATION_IDS = ["CYYZ", "OMDB", "LTFM", "KLAX", "WIII"]

INSTRUCTIONS = (
    "You are an AI assistant specialized in interpreting and describing weather data stored in JSON format. "
    "You are expert at reading weather data for a given location and providing an English description of the weather at that location. "
    "The English weather description should be no more than 280 words and in the style of TV weatherman."
)
PROMPT = (
    "Briefly describe the weather for the location identified in the following JSON data. "
    "Format your response as a JSON object with the following key: 'weather_description'. "
)


class Metars:
    base_url = "https://aviationweather.gov/api/data/metar"

    def _relative_humidity(temperature, dewpoint):
        # https://en.wikipedia.org/wiki/Clausius%E2%80%93Clapeyron_relation#Meteorology_and_climatology
        pp = math.exp((17.625 * dewpoint) / (243.04 + dewpoint))
        svp = math.exp((17.625 * temperature) / (243.04 + temperature))
        return round(100 * pp / svp, 1)

    def _decode_wx(wx, precip = {
            "VC" : "In the vicinity",
            "MI" : "Shallow",
            "PR" : "Partial",
            "BC" : "Patches",
            "DR" : "Low drifting",
            "BL" : "Blowing",
            "SH" : "Showers",
            "TS" : "Thunderstorm",
            "FZ" : "Freezing",
            "RA" : "Rain",
            "DZ" : "Drizzle",
            "SN" : "Snow",
            "SG" : "Snow Grains",
            "IC" : "Ice Crystals",
            "PL" : "Ice Pellets",
            "GR" : "Hail",
            "GS" : "Graupel",
            "UP" : "Precipitation",
            "FG" : "Fog",
            "VA" : "Volcanic Ash",
            "BR" : "Mist",
            "HZ" : "Haze",
            "DU" : "Widespread Dust",
            "FU" : "Smoke",
            "SA" : "Sand",
            "PY" : "Spray",
            "SQ" : "Squall",
            "PO" : "Dust",
            "DS" : "Duststorm",
            "SS" : "Sandstorm",
            "FC" : "Funnel Cloud",
        }):
        description = ""
        if wx[0] == "-":
            description += "Light "
            wx = wx[1:]
        elif wx[0] == "+":
            description += "Heavy "
            wx = wx[1:]
        elif wx[:2] == "VC":
            wx = wx[2:] + "VC"
        else:
            description += "Moderate "
        while len(wx) > 1:
            code = wx[:2]
            wx = wx[2:]
            description += " ".join(description, precip[code])
        return description.lower()


    def __init__(self, station_id: str):
        self.station_id = station_id
        self.request_args = {
            "ids": station_id,
            "format": "geojson",
            "taf": False,
            "hours": 1,
        }

    def download(self):
        params = urllib.parse.urlencode(self.request_args)
        url = f"{Metars.base_url}?{params}"
        print("Downloading new METARS data from", url)

        resp = requests.get(url)
        if resp.status_code != 200:
            print("Error downloading METARS", resp.status_code)
            return
        metars_json = json.loads(resp.text)["features"][0]
        self.weather = metars_json["properties"]
        self.weather["geometry"] = metars_json["geometry"]
        self._add_weather_fields()

    def weather_report(
        self, client: openai.OpenAI, model: str, sys_prompt: str, prompt: str
    ):
        print(f"Generating weather report for {self.station_id}")
        weather = self._weather_summary()
        msgs = [{"role": "system", "content": sys_prompt}]
        content = [
            {
                "type": "text",
                "text": f"{prompt} \n\nWEATHER DATA: {json.dumps(weather)}",
            }
        ]
        msgs.append({"role": "user", "content": content})
        response = gpt_chat(client=client, model=model, messages=msgs)
        self.weather["weather_description"] = json.loads(response)

    def _weather_summary(self, summary_params = {
            "temperature_c": "temp",
            "relative_humidity": "rh",
            "wind_speed_kmph": "wspd_kmph",
            "wind_gust_kmph": "wgst_kmph"
        }):
        summary = {"station_name": self.weather["site"]}
        for long_name, short_name in summary_params.items():
            if short_name in self.weather:
                summary.update({long_name: self.weather[short_name]})
        return summary

    def _add_weather_fields(self):      
        # time_utc = self.weather.get("obsTime")  # TODO: Convert to local

        wx = self.weather.get("wx", None)
        if wx:
            self.weather["wx_descrip"] = Metars._decode_wx(wx)

        wspd = self.weather.get("wspd", None)
        if wspd:
            self.weather["wspd_kmph"] = round(wspd * 1.852, 1)

        wgst = self.weather.get("wgst", None)
        if wgst:
            self.weather["wgst_kmph"] = round(wgst * 1.852, 1)

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
    metars = [Metars(s_id) for s_id in STATION_IDS]
    openai_client = openai.OpenAI()

    for m in metars:
        print(m.station_id)
        m.download()
        m.weather_report(
            openai_client, model="gpt-4o-mini", sys_prompt=INSTRUCTIONS, prompt=PROMPT
        )
        print(m.weather)

    # gpt_weather_report(
    #     metars=metars, client=openai_client, model="gpt-4o-mini", max_tokens=1000
    # )
    # with open("data/metars/current-weather.json", "w") as f:
    #     json.dump(metars, f, indent=4)


if __name__ == "__main__":
    main()
