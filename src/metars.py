import os
import requests

def download_metars(save_folder, url="https://aviationweather.gov/data/cache/metars.cache.xml"):
    print("Downloading new METARS data from", url)
    resp = requests.get(url)
    if resp.status_code == 200:
        filename = os.path.basename(url)
        with open(f"{save_folder}/{filename}", "w") as metars_file:
            metars_file.write(resp.text)
    else:
        print("Error downloading METARS", resp.status_code)

def main():
    download_metars(save_folder="data/metars")

if __name__ == "__main__":
    main()