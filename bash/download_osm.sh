#!/usr/bin/env bash

# Import OpenStreetMap data from Geofabrik server

wget download.geofabrik.de/europe/france/$1-latest.osm.pbf
osmconvert $1-latest.osm.pbf -o=$1.o5m
osmfilter $1.o5m --keep="power=*" -o=$1_power.o5m