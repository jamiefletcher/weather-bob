#!/bin/bash

## download metars
curl "https://aviationweather.gov/data/cache/metars.cache.xml.gz" | gunzip -c > data/metars/metars.cache.xml

## tafs
# https://aviationweather.gov/data/cache/tafs.cache.xml.gz | gunzip -c > data/metars/tafs.cache.xml