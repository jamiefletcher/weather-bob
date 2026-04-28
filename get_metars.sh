#!/bin/bash

## download metars
curl "https://aviationweather.gov/data/cache/metars.cache.csv" > data/metars/metars.csv
## tafs
#curl https://aviationweather.gov/data/cache/tafs.cache.xml | gunzip -c > data/metars/tafs.csv

ogr2ogr data/metars/metars.gpkg data/metars/metars.vrt

## join to airports_large
rm -rf data/metars/metars.geojson
ogr2ogr -f GeoJSON data/metars/metars.geojson -dialect SQLITE -sql "SELECT m.*, p.municipality, p.continent, p.iso_country, p.iso_region, p.wikipedia_link FROM airports_large p INNER JOIN metars m ON m.station_id = p.icao_code" data/metars/metars_airports.vrt

rm -rf data/metars/metars.gpkg