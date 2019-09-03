# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# import
import re

from netCDF4 import Dataset, date2num
from datetime import datetime
import os
import pandas as pd

# __all__ = []
# __version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


def build_net_cdf():
    """ Example on how to build a net cdf

    :return:
    """
    # Directory with station data
    station_dir = "/home/benjamin/ownCloud/Post-doc Guyane/Rainfall - conventional weather stations - RS"

    # Number of stations
    nb_stations = len([name for name in os.listdir(station_dir) if os.path.isfile(name)])

    # Create a daily DatetimeIndex range
    # Replace 'days' by 'hours' or 'minute', etc. if station time step is lower
    time_units = "days since 0001-01-01 00:00:00.0"
    dates = pd.date_range("01-Jan-1950", "01-Jan-2018", freq='D')
    dates_num = date2num(dates.to_pydatetime(), units=time_units)

    # Create Dataset
    data = Dataset('test.nc', "w")

    # Create dimensions
    time = data.createDimension("time", len(dates))
    lat = data.createDimension("lat", nb_stations)
    lon = data.createDimension("lon", nb_stations)
    # alt = data.createDimension("alt")

    # Create variables
    times = data.createVariable("time", "f8", ("time",))
    latitudes = data.createVariable("lat", "f4", ("lat",))
    longitudes = data.createVariable("lon", "f4", ("lon",))
    rainfalls = data.createVariable("rainfall", "f4", ("lat", "lon", "time",))

    for root, _, files in os.walk(station_dir):
        for name in files:
            latitude, longitude, altitude = read_header(os.path.join(root, name))
            dataframe = pd.read_csv(os.path.join(root, name), header=16)

            time_extent = date2num(pd.DatetimeIndex([dataframe["Data"][0], dataframe["Data"][-1]]).to_pydatetime(),
                                   units=time_units)




def read_header(station_file):

    num_line = 0
    latitude = longitude = altitude = None
    with open(station_file) as file:
        for line in file.readlines():
            num_line += 1
            if "Latitude" in line:
                latitude = float(re.search('[-+]?\d+\.\d+', line).group(0))
            elif "Longitude" in line:
                longitude = float(re.search('[-+]?\d+\.\d+', line).group(0))
            elif "Altitude" in line:
                altitude = float(re.search('[-+]?\d+\.\d+', line).group(0))
            if num_line > 20:
                break
    return latitude, longitude, altitude


def get_station_value_in_net_cdf(lat, lon, time):
    pass


if __name__ == "__main__":
    build_net_cdf()
