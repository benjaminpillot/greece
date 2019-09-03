# -*- coding: utf-8 -*-

""" Solar radiation methods and classes

More detailed description.
"""
from numpy import zeros, diff, argwhere, interp, trapz
from pandas import Series, DatetimeIndex, TimedeltaIndex, Timedelta

from greece.solartools.geometry import get_sunrise_and_sunset

__version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


def irradiance_to_irradiation(irradiance, time, location, method='integration'):
    """ Convert irradiance to irradiation (or power to energy for pv systems)

    Here, irradiance may have non-monotonic time index. Integration is
    performed from sunrise to sunset hours. The result is very accurate
    but much slower than with monotonic and no sunrise/sunset hours.
    :param irradiance: pandas Series of irradiance/power values
    :param time: time for which we must integrate irradiance (DatetimeIndex)
    :param location: pvlib location object
    :param method: 'integration', 'mean'
    :return: pandas Series of irradiation values
    """
    if method == 'integration':

        irradiance_day = irradiance.index.floor("D").drop_duplicates(keep="first")
        sunrise, sunset = get_sunrise_and_sunset(irradiance_day, location)
        sunrise_and_sunset = sunrise.append(sunset)
        irradiance = irradiance.append(Series(data=[0] * len(sunrise_and_sunset),
                                              index=sunrise_and_sunset)).sort_index()
        irradiance_julian_time = Series(irradiance.index.to_julian_date(), irradiance.index)
        irradiation_julian_time = Series(time.to_julian_date(), time)

        # Add interp values to irradiance and julian time
        irradiance_interp = interp(irradiation_julian_time.values, irradiance_julian_time.values, irradiance.values)
        irradiance = irradiance.append(Series(data=irradiance_interp, index=time)).sort_index()
        irradiance = irradiance[~irradiance.index.duplicated(keep="first")]
        irradiance_julian_time = Series(irradiance.index.to_julian_date(), irradiance.index)

        # Compute values and times corresponding to time for which we must integrate
        values = [irradiance[idx_1:idx].values for idx_1, idx in zip(time[0:-1:], time[1::])]
        times = [irradiance_julian_time[idx_1:idx].values for idx_1, idx in zip(time[0:-1:], time[1::])]

        # Final data
        data = [24 * trapz(val, ttime) for val, ttime in zip(values, times)]

    elif method == 'mean':

        delta = Timedelta("1H")
        time_step = time[1::] - time[:-1]
        data = [val * 2 * (t_1 - t_1_2) / delta if t_1 - t_1_2 <= step/2 else
                val * 2 * (t_1_2 - t_0) / delta for val, t_0, t_1, t_1_2, step in
                zip(irradiance.values, time[:-1], time[1::], irradiance.index, time_step)]

    else:
        data = []

    return Series(data=data, index=time[:-1])


def irradiation_to_irradiance(irradiation, location=None):
    """ Convert irradiation to irradiance

    :param irradiation: Series of irradiation values
    :param location:
    :return:
    """
    time = irradiation.index
    time_step = TimedeltaIndex([time[1] - time[0]]).append(time[1::] - time[:-1])
    new_time = Series(time + time_step/2)
    new_values = irradiation.values * 3600 / time_step.seconds.values

    # Compute sunrise and sunset if not provided
    sunrise, sunset = get_sunrise_and_sunset(time, location)

    # Sunrise/sunset index stands for the moment when time stamp overpasses sunrise/sunset time
    # A little bit more tricky for sunrise since irradiation time index
    # is defined with respect to: 06:00 stands for the irradiation from
    # 06:00 to 07:00 (as the SAM PV model)
    sunrise_idx = zeros(len(new_time))
    sunset_idx = sunrise_idx.copy()
    sunrise_idx[sunrise < time] = 1
    sunset_idx[sunset > time] = 1
    sunrise_idx = argwhere(diff(sunrise_idx) == 1).squeeze()
    sunset_idx = argwhere(diff(sunset_idx) == -1).squeeze()

    # Compute time and corresponding values
    new_time.values[sunrise_idx] = time[sunrise_idx + 1] - (time[sunrise_idx + 1] - sunrise[sunrise_idx + 1])/2
    new_time.values[sunset_idx] = time[sunset_idx] + (sunset[sunset_idx] - time[sunset_idx])/2
    new_values[sunrise_idx] = new_values[sunrise_idx] * 3600/(time[sunrise_idx + 1] - sunrise[sunrise_idx]).seconds
    new_values[sunset_idx] = new_values[sunset_idx] * 3600/(sunset[sunset_idx] - time[sunset_idx]).seconds

    return Series(new_values, DatetimeIndex(new_time).round("s"))


if __name__ == "__main__":
    from pandas import date_range
    from pvlib.location import Location
    from greece.solartools.radiation import generate_synthetic_irradiation, generate_toa_sequence
    from gistools.utils.sys.timer import Timer

    loc = Location(5, -50, tz='America/Cayenne')
    time_h = date_range("1/1/2011 0:00", "1/1/2012 0:00", freq="1H", tz=loc.tz)
    toa = generate_synthetic_irradiation(loc, time_h, accuracy="30min")
    toa_r = generate_toa_sequence(date_range("1/1/2011", "1/1/2012", freq="10min", tz=loc.tz), loc)
    test = irradiation_to_irradiance(toa, location=loc)
    # with Timer() as t:
    #     sun_rise = get_sun_rise_set_transit(toa.index, loc.latitude, loc.longitude)
    # print("time sunrise: %s" % t)
    with Timer() as t:
        # test_2 = irradiance_to_irradiation(toa_r, time_h, loc)
        test_3 = irradiance_to_irradiation(test, time_h, loc, 'mean')
    print("time: %s" % t)
    # print(test)
    # print(test_2)
    print(test_3)
    print(test)
    # print(toa)
    # print(test_2)
