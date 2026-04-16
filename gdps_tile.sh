#!/bin/bash

rm -rf data/gdps/tiles/*
gdal raster pipeline read data/gdps/001.grib2 \
    ! color-map --color-map 'data/white-black.txt' --add-alpha --color-selection interpolate \
    ! reproject --dst-crs='EPSG:3857' \
    ! tile data/gdps/tiles/ \
        --add-alpha --skip-blank --min-zoom 0 --max-zoom 3