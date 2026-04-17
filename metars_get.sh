#!/bin/bash

### download metars
curl "https://aviationweather.gov/data/cache/metars.cache.csv.gz" | gunzip -c > data/metars/metars.csv