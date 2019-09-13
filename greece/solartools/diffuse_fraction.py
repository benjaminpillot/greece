# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""
import numpy as np
from pandas import DataFrame, date_range, Series
from utils.check import type_assert
from utils.sys.timer import Timer

from greece.solartools.geometry import get_solar_position
from greece.solartools.radiation import generate_toa_sequence, generate_clearsky_sequence

__version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


@type_assert(ghi=Series)
def erbs(ghi, location=None, sun_position=None, kt=None):
    """ Retrieve DNI and DHI from GHI using Erbs model

    :param ghi: Series of GHI values
    :param location:
    :param sun_position:
    :param kt: clearness index
    :return: dhi and dni
    """
    if sun_position is None:
        try:
            sun_position = get_solar_position(ghi.index, location.latitude, location.longitude, location.altitude)
        except AttributeError:
            raise ValueError("Either 'location' or 'sun_position' argument must be passed")

    if kt is None:
        toa = generate_toa_sequence(ghi.index, sun_position=sun_position)
        kt = ghi/toa
        kt[toa == 0] = 0

    # Diffuse fraction
    # kt <= 0.22
    kd = 1 - 0.09*kt

    # kt > 0.22 and kt <= 0.8
    kd = kd.where((kt <= 0.22) | (kt > 0.8), 0.9511 - 0.1604*kt + 4.388*kt**2 - 16.638*kt**3 + 12.336*kt**4)

    # kt > 0.8
    kd[kt > 0.8] = 0.165

    dhi = kd * ghi
    dni = (ghi - dhi)/np.cos(sun_position["zenith"] * np.pi/180)

    return DataFrame({'dni': dni, 'dhi': dhi, 'kt': kt, 'kd': kd})


if __name__ == "__main__":
    import pvlib
    time = date_range("1/1/2011", "12/31/2011", freq="30 min")
    loc = pvlib.location.Location(42, 9)
    sun_pos = get_solar_position(time, loc.latitude, loc.longitude, loc.altitude)
    clearsky = generate_clearsky_sequence(time, loc)
    with Timer() as t:
        diff_frac = erbs(clearsky, location=loc)
    print("time: %s" % t)
    for col in diff_frac:
        print(col)
