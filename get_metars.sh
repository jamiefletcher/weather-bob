#!/bin/bash

## download metars
curl "https://aviationweather.gov/data/cache/metars.cache.xml" > data/metars/metars.cache.xml

## tafs
#curl https://aviationweather.gov/data/cache/tafs.cache.xml | gunzip -c > data/metars/tafs.csv

# ogr2ogr data/metars/metars.gpkg data/metars/metars.vrt
