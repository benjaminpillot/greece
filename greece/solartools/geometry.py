# -*- coding: utf-8 -*-

""" Solar geometry methods and classes

More detailed description.
"""
from pvlib.solarposition import get_sun_rise_set_transit
from pandas import DatetimeIndex

# __all__ = ["Surface", "SunPosition", "_sun_position"]
# __version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2017, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


def get_sunrise_and_sunset(time, location):
    """ Get sunrise and sunset times

    :param time:
    :param location:
    :return:
    """
    # try:
    #     time_utc = time.floor("D").tz_convert('UTC')  # Use 'floor' to be sure we have sunrise/sunset of the right day
    # except TypeError:
    #     time_utc = time.floor("D").tz_localize('UTC')

    # sun_rise_set = get_sun_rise_set_transit(time_utc, location.latitude, location.longitude)
    sun_rise_set = get_sun_rise_set_transit(time, location.latitude, location.longitude)

    # if time.tz is None:
    #     to_tz = location.tz
    # else:
    #     to_tz = time.tz

    # sunrise = DatetimeIndex(sun_rise_set["sunrise"].values, tz=time_utc.tz).tz_convert(to_tz)
    # sunset = DatetimeIndex(sun_rise_set["sunset"].values, tz=time_utc.tz).tz_convert(to_tz)
    # sunrise = DatetimeIndex(sun_rise_set["sunrise"])
    # sunset = DatetimeIndex(sun_rise_set["sunset"])

    # return sunrise, sunset
    return DatetimeIndex(sun_rise_set["sunrise"]), DatetimeIndex(sun_rise_set["sunset"])
