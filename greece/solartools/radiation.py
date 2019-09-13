# -*- coding: utf-8 -*-

""" Solar radiation methods and classes

More detailed description.
"""
from calendar import monthrange

import numpy as np
from numba import jit, float64, int64

from pvlib.atmosphere import get_relative_airmass, get_absolute_airmass
from pvlib.clearsky import lookup_linke_turbidity, ineichen
from pvlib.irradiance import get_extra_radiation
from pandas import date_range, Timedelta, Series, DataFrame, Timestamp

from greece.solartools.geometry import get_sunrise_and_sunset, get_solar_position

__version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


# Specific constants
SOLAR_CONSTANT = 1367.  # Solar constant in W/m² (value recommended by WMO)


def to_decimal_time(index):
    """

    :param index: DatetimeIndex
    :return:
    """
    time = index.hour + (index.minute * 60 + index.second) / 3600
    try:
        return time.to_numpy()
    except AttributeError:
        return time


def generate_synthetic_clear_sky_irradiation(time, location, sun_position=None, accuracy="30min"):
    """

    :param time:
    :param location:
    :param sun_position:
    :param accuracy:
    :return:
    """
    return generate_synthetic_irradiation(location, time, "clearsky", accuracy, sun_position)


def generate_synthetic_toa_irradiation(time, location=None, sun_position=None, accuracy="30min"):
    """

    :param time:
    :param location:
    :param sun_position: solar position corresponding to time with freq=accuracy
    :param accuracy:
    :return:
    """
    return generate_synthetic_irradiation(location, time, "toa", accuracy, sun_position)


def generate_synthetic_irradiation(location, time, i_type="toa", accuracy="30min", sun_position=None):
    """ Generate clearsky/toa irradiation synthetic time series

    Integration is not performed from sunrise to sunset for performance
    purposes. Prefer using a small "accuracy" when precision is required.
    :param location:
    :param time:
    :param i_type: irradiance type ("toa", "clearsky", "both")
    :param accuracy: time step used for generating toa irradiance before integration
    :param sun_position:
    :return:
    """
    dt = Timedelta(accuracy)/Timedelta("1H")

    if sun_position is None:
        time_sequence = date_range(time[0], time[-1], freq=accuracy)
    else:
        time_sequence = sun_position.index

    if i_type == "toa":
        irr = generate_toa_sequence(time_sequence, location, sun_position)
    else:
        irr = generate_clearsky_sequence(time_sequence, location, sun_position)

    ts = [irr[idx_1:idx].values for idx_1, idx in zip(time[0:-1:], time[1::])]

    return Series(np.trapz(ts, dx=dt), time[:-1])


def generate_clearsky_sequence(time, location, sun_position=None, p_0=101325.0, model="ineichen"):

    """ Generate clear-sky irradiance sequence

    :param time:
    :param location: pvlib.location.Location object
    :param sun_position:
    :param p_0: sea level pressure
    :param model: {'ineichen', 'solis'} #TODO: implement solis clearsky model
    :return:
    """
    if sun_position is None:
        sun_position = get_solar_position(time, location.latitude, location.longitude, location.altitude)

    # Altitude corrected (King et al. 1997; Rigollier et al. 2000)
    pressure = p_0 * np.exp(-0.0001184 * location.altitude)

    # Relative airmass
    am = get_relative_airmass(sun_position["zenith"])

    # Absolute airmass
    am_a = get_absolute_airmass(am, pressure)

    # Linke turbidity
    linke_turbidity = lookup_linke_turbidity(time, location.latitude, location.longitude)

    if model == "ineichen":
        return ineichen(sun_position["apparent_zenith"], am_a, linke_turbidity)["ghi"]
    elif model == "solis":
        pass


def generate_toa_sequence(time, location=None, sun_position=None):
    """ Generate TOA irradiance sequence

    :param time:
    :param location: pvlib.location.Location object
    :param  sun_position:
    :return:
    """
    if sun_position is None:
        try:
            sun_position = get_solar_position(time, location.latitude, location.longitude, location.altitude)
        except AttributeError:
            raise ValueError("Either 'location' or 'sun_position' must be passed as input argument")

    return Series(toa_radiation(sun_position["elevation"]), time)


def toa_radiation(elevation):
    """ Compute TOA radiation

    :param elevation: TimeSeries/Series object
    :return toa
    :rtype: collection
    """

    def _toa_radiation():
        toa = get_extra_radiation(elevation.index, SOLAR_CONSTANT) * np.sin(elevation.values * np.pi/180)
        toa[toa < 0] = 0
        return toa

    return _toa_radiation()


def generate_hourly_ghi_sequence(daily_kt, daily_kc, daily_toa, location, accuracy="30min", base_year=2018,
                                 tolerance=0.05):
    """ Generate sequence of hourly Global Horizontal Irradiation

    :param daily_kt: Series of daily kt values
    :param daily_kc: Series of daily kc values
    :param daily_toa: Series of daily TOA irradiation values
    :param location: pvlib.location.Location object
    :param accuracy:
    :param base_year:
    :param tolerance: relative tolerance for resulting GHI
    :return: Series of hourly GHI
    """
    time_centre = date_range("1/1/%d 0:30" % base_year, '12/31/%d 23:30' % base_year, freq="1H", tz=location.tz)
    time_hourly = date_range("1/1/%d 0:00" % base_year, "1/1/%d 0:00" % (base_year + 1), freq="1H", tz=location.tz)
    sun_position = get_solar_position(time_centre, location.latitude, location.longitude, location.altitude)
    sunrise, sunset = get_sunrise_and_sunset(daily_kc.index, location)
    df = generate_synthetic_clearsky_clearness_index(location, time_hourly, accuracy=accuracy)
    hourly_kt = Series(generate_hourly_kt_sequence(daily_kt, daily_kc, daily_toa, sun_position["apparent_elevation"],
                                                   sunrise, sunset, df, tolerance), df.index)

    ghi = df["toa"] * hourly_kt

    return ghi


def generate_daily_clear_sky_sequence(location, accuracy, base_year):
    """ Generate sequence of clear-sky irradiation over the year

    :param location:
    :param accuracy:
    :param base_year:
    :return:
    """
    return generate_synthetic_clear_sky_irradiation(date_range("1/1/%d" % base_year, "1/1/%d" % (base_year + 1),
                                                               freq="1D", tz=location.tz), location, accuracy=accuracy)


def generate_daily_toa_sequence(location, accuracy, base_year):
    """ Generate sequence of toa irradiation over the year

    :param location:
    :param accuracy:
    :param base_year:
    :return:
    """
    return generate_synthetic_irradiation(location, date_range("1/1/%d" % base_year, "1/1/%d" % (base_year + 1),
                                          freq="1D", tz=location.tz), i_type="toa", accuracy=accuracy)


def generate_daily_toa_and_clear_sky_sequence(location, accuracy, base_year):
    """ Generate sequence of daily TOA and clear-sky irradiation over the year

    Compute both at the same time in order to speed up computation
    :param location:
    :param accuracy:
    :param base_year:
    :return:
    """
    time = date_range("1/1/%d" % base_year, "1/1/%d" % (base_year + 1), freq="1D", tz=location.tz)
    sun_position = get_solar_position(date_range(time[0], time[-1], freq=accuracy), location.latitude,
                                      location.longitude, location.altitude)

    return generate_synthetic_toa_irradiation(time, location, sun_position, accuracy), \
        generate_synthetic_clear_sky_irradiation(time, location, sun_position, accuracy)


def generate_synthetic_clearsky_clearness_index(location, time, accuracy="30min", sun_position=None):
    """ Generate clearsky kt synthetic time series

    :param location:
    :param time:
    :param accuracy:
    :param sun_position
    :return: DataFrame with kt, clearsky and toa columns
    """

    if sun_position is None:
        sun_position = get_solar_position(date_range(time[0], time[-1], freq=accuracy), location.latitude,
                                          location.longitude, location.altitude)
    clearsky = generate_synthetic_clear_sky_irradiation(time, location, sun_position=sun_position, accuracy=accuracy)
    toa = generate_synthetic_toa_irradiation(time, location, sun_position=sun_position, accuracy=accuracy)

    kt = clearsky / toa
    kt[toa == 0] = 0

    return DataFrame({"kt": kt, "clearsky": clearsky, "toa": toa})


def generate_clearsky_clearness_index_sequence(location, time, sun_position=None):
    """ Generate clear-sky kt and toa/cls irradiance time series

    :param location:
    :param time:
    :param sun_position:
    :return:
    """
    if sun_position is None:
        sun_position = get_solar_position(time, location.latitude, location.longitude, location.altitude)
    clearsky = generate_clearsky_sequence(time, location, sun_position)
    toa = generate_toa_sequence(time, sun_position=sun_position)
    kt = clearsky / toa
    kt[toa == 0] = 0

    return DataFrame({"kt": kt, "clearsky": clearsky, "toa": toa})


def generate_daily_kc_sequence(kcm, base_year, tz="UTC", tolerance=0.01):
    """ Generate sequence of daily clearsky index kc over the year

    :param kcm: list of mean monthly kc
    :param base_year:
    :param tz: time zone
    :param tolerance: algorithm tolerance for kc statistical convergence
    :return: Series of daily kc
    """
    kc = generate_daily_kc_sequence_over_month(kcm[0], kcm[0], 1, base_year, tz, tolerance)
    for _kcm, month in zip(kcm[1::], range(2, 13)):
        kc0 = kc[-1]
        kc = kc.append(generate_daily_kc_sequence_over_month(_kcm, kc0, month, base_year, tz, tolerance))

    return kc


def generate_daily_kc_sequence_over_month(kcm, kc0, month, base_year, tz="UTC", tolerance=0.02):
    """ Generate sequence of daily clearsky index kc over the month

    :param kcm:
    :param kc0: first value of the month
    :param month:
    :param base_year:
    :param tz: time zone
    :param tolerance:
    :return:
    """
    nd = monthrange(base_year, month)[1]
    start = Timestamp(base_year, month, 1)
    end = Timestamp(base_year, month, nd)
    nb_iterations = 0

    if isinstance(kcm, list):
        while "it is not within range":
            rd = np.random.rand(nd + 1)
            kc = _generate_daily_kc(np.mean(kcm), np.mean(kc0), nd + 1, rd)[1::]  # Warning: use mean(kcm)
            # to avoid different transition Markov matrices for almost similar Kcm !!
            tol = tolerance if nb_iterations < 200 else 0.04
            if abs(np.mean(kc) - np.mean(kcm)) / np.mean(kcm) <= tol:
                return [Series(data=kc, index=date_range(start, end, freq="1D", tz=tz)) for _ in range(len(kcm))]
            nb_iterations += 1
    else:
        while "it is not within range":
            daily_kc = _generate_daily_kc(kcm, kc0, nd + 1)
            tol = tolerance if nb_iterations < 200 else 0.04
            if abs(np.mean(daily_kc[1::]) - kcm) / kcm <= tol:
                return Series(data=daily_kc[1::], index=date_range(start, end, freq="1D", tz=tz))
            nb_iterations += 1


def generate_hourly_kt_sequence(daily_kt, daily_kc, daily_toa, sun_elevation, sunrise, sunset, kcs_df,
                                tolerance=0.05, max_iter=10):
    """ Generate sequence of hourly kt

    :param daily_kt: Timeseries of daily kt values
    :param daily_kc: Timeseries of daily kc values
    :param daily_toa: Timeseries of daily TOA irradiation
    :param sun_elevation: sun elevation of hour centres
    :param sunrise: sun rise of the corresponding days (DatetimeIndex)
    :param sunset: sun set of the corresponding days (DatetimeIndex)
    :param kcs_df: clearsky kt dataframe (kt, toa, cls)
    :param tolerance: relative tolerance for corresponding hourly GHI
    :param max_iter: maximum number of iterations when generating hourly kt over the day
    :return:
    """
    hourly_kt = []
    for day, sun_r, sun_s in zip(daily_kt.index, sunrise, sunset):
        daily_time = (sun_elevation.index.year == day.year) & (sun_elevation.index.month == day.month) &\
                     (sun_elevation.index.day == day.day)
        daily_elevation = sun_elevation[daily_time].values
        time = to_decimal_time(sun_elevation[daily_time].index)
        sun_rise = to_decimal_time(sun_r)
        sun_set = to_decimal_time(sun_s)
        kt_cls = kcs_df["kt"].loc[daily_time].values
        toa_h = kcs_df["toa"].loc[daily_time].values

        while "it is not within range":

            kt = _generate_hourly_kt_over_day(daily_elevation, time, daily_kt[day], daily_kc[day], kt_cls, sun_rise,
                                              sun_set, max_iter)

            if abs(np.sum(kt * toa_h) - daily_kt[day] * daily_toa[day]) / (daily_kt[day] * daily_toa[day]) < tolerance:
                break

        hourly_kt.extend(kt)

    return hourly_kt


def _generate_daily_kc(kcm, kc0, nd, rd=None):
    """
    Generates a sequence of synthetic daily clearsky indices (kc) using the mean monthly clear-sky
    index as the input. The algorithm is based on the method by Aguiar et al in the paper:

    R. Aguiar and M. Collares-Pereira, "A simple procedure for the generation of sequences of
      daily radiation values using Markov transition matrices", Solar Energy, vol. 40, 269-279, 1988

    And modified with respect to MeteoNorm's theory documentation.
    Thanks to Stephen Kaplan (https://github.com/stephenkaplan/synthetic8760)

    Inputs: ktm is the mean clearness index for the month
            kc0 is initial clearness index (on the first day of the month)
            nd is the number of daily clearness indices to generate

    Copyright (C) 2014 Julius Susanto and 2018 Stephen Kaplan

    :param kcm: monthly mean kc
    :param kc0: first kc value of the month
    :param nd: number of days in month
    :param rd: list of uniform random numbers

    :return:
    """
    if rd is None:
        rd = np.random.rand(nd)

    # Markov Transition Matrices
    mtm_lib = {}

    mtm_states = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
    mtm_min = [0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05]
    mtm_max = [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]

    # 0.10 < kc <= 0.20
    mtm_lib[0] = np.matrix([[0.500, 0.280, 0.150, 0.050, 0.020, 0.000, 0.000, 0.000, 0.000, 0.000],
                            [0.200, 0.480, 0.200, 0.100, 0.020, 0.000, 0.000, 0.000, 0.000, 0.000],
                            [0.050, 0.200, 0.480, 0.200, 0.050, 0.020, 0.000, 0.000, 0.000, 0.000],
                            [0.020, 0.050, 0.180, 0.500, 0.180, 0.050, 0.020, 0.000, 0.000, 0.000],
                            [0.000, 0.020, 0.050, 0.180, 0.500, 0.180, 0.050, 0.020, 0.000, 0.000],
                            [0.000, 0.000, 0.020, 0.050, 0.180, 0.500, 0.180, 0.050, 0.020, 0.000],
                            [0.000, 0.000, 0.000, 0.000, 0.050, 0.200, 0.300, 0.200, 0.000, 0.250],
                            [0.000, 0.000, 0.000, 0.000, 0.020, 0.050, 0.200, 0.480, 0.200, 0.050],
                            [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.050, 0.200, 0.500, 0.250],
                            [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.200, 0.050, 0.050, 0.700]])

    # 0.20 < kc <= 0.30
    mtm_lib[1] = np.matrix([[0.500, 0.280, 0.150, 0.050, 0.020, 0.000, 0.000, 0.000, 0.000, 0.000],
                            [0.200, 0.480, 0.200, 0.100, 0.020, 0.000, 0.000, 0.000, 0.000, 0.000],
                            [0.100, 0.650, 0.200, 0.050, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
                            [0.000, 0.250, 0.000, 0.050, 0.300, 0.050, 0.000, 0.000, 0.050, 0.300],
                            [0.000, 0.400, 0.050, 0.100, 0.400, 0.050, 0.000, 0.000, 0.000, 0.000],
                            [0.000, 0.000, 0.000, 0.000, 0.250, 0.500, 0.250, 0.000, 0.000, 0.000],
                            [0.000, 0.000, 0.000, 0.000, 0.000, 0.250, 0.500, 0.250, 0.000, 0.000],
                            [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.250, 0.500, 0.250, 0.000],
                            [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.250, 0.500, 0.250],
                            [0.000, 0.000, 0.000, 0.000, 0.000, 0.700, 0.050, 0.000, 0.000, 0.250]])

    # 0.30 < kc <= 0.40
    mtm_lib[2] = np.matrix([[0.133, 0.319, 0.204, 0.115, 0.074, 0.033, 0.030, 0.044, 0.011, 0.037],
                            [0.081, 0.303, 0.232, 0.127, 0.088, 0.060, 0.029, 0.031, 0.018, 0.033],
                            [0.036, 0.195, 0.379, 0.135, 0.087, 0.039, 0.042, 0.027, 0.025, 0.036],
                            [0.032, 0.190, 0.205, 0.189, 0.119, 0.069, 0.059, 0.038, 0.045, 0.054],
                            [0.051, 0.175, 0.189, 0.185, 0.140, 0.079, 0.060, 0.040, 0.017, 0.064],
                            [0.042, 0.213, 0.243, 0.126, 0.117, 0.090, 0.045, 0.036, 0.021, 0.069],
                            [0.017, 0.166, 0.237, 0.141, 0.100, 0.091, 0.054, 0.062, 0.046, 0.087],
                            [0.038, 0.171, 0.190, 0.133, 0.095, 0.090, 0.057, 0.062, 0.043, 0.119],
                            [0.044, 0.093, 0.231, 0.143, 0.115, 0.066, 0.038, 0.060, 0.099, 0.110],
                            [0.029, 0.131, 0.163, 0.127, 0.062, 0.092, 0.065, 0.072, 0.078, 0.180]])

    # 0.40 < kc <= 0.50
    mtm_lib[3] = np.matrix([[0.116, 0.223, 0.196, 0.129, 0.093, 0.077, 0.054, 0.044, 0.032, 0.037],
                            [0.051, 0.228, 0.199, 0.143, 0.101, 0.083, 0.065, 0.052, 0.035, 0.043],
                            [0.028, 0.146, 0.244, 0.156, 0.120, 0.092, 0.069, 0.053, 0.040, 0.052],
                            [0.020, 0.111, 0.175, 0.208, 0.146, 0.104, 0.074, 0.067, 0.044, 0.052],
                            [0.017, 0.115, 0.161, 0.177, 0.155, 0.102, 0.085, 0.067, 0.054, 0.068],
                            [0.018, 0.114, 0.147, 0.156, 0.142, 0.123, 0.088, 0.075, 0.060, 0.077],
                            [0.019, 0.116, 0.152, 0.153, 0.133, 0.100, 0.090, 0.078, 0.061, 0.098],
                            [0.022, 0.105, 0.145, 0.134, 0.112, 0.109, 0.103, 0.085, 0.077, 0.108],
                            [0.016, 0.100, 0.119, 0.120, 0.100, 0.105, 0.099, 0.096, 0.120, 0.126],
                            [0.012, 0.081, 0.109, 0.115, 0.101, 0.082, 0.075, 0.091, 0.107, 0.226]])

    # 0.50 < kc <= 0.60
    mtm_lib[4] = np.matrix([[0.095, 0.201, 0.140, 0.121, 0.112, 0.076, 0.073, 0.066, 0.055, 0.061],
                            [0.029, 0.176, 0.158, 0.133, 0.121, 0.096, 0.078, 0.079, 0.067, 0.063],
                            [0.015, 0.096, 0.171, 0.157, 0.139, 0.121, 0.093, 0.080, 0.066, 0.062],
                            [0.008, 0.055, 0.103, 0.199, 0.186, 0.130, 0.108, 0.085, 0.063, 0.063],
                            [0.006, 0.039, 0.077, 0.145, 0.236, 0.167, 0.113, 0.083, 0.064, 0.069],
                            [0.006, 0.044, 0.080, 0.128, 0.192, 0.166, 0.123, 0.100, 0.081, 0.080],
                            [0.006, 0.049, 0.082, 0.132, 0.152, 0.139, 0.125, 0.110, 0.095, 0.109],
                            [0.007, 0.047, 0.086, 0.113, 0.138, 0.125, 0.114, 0.124, 0.112, 0.134],
                            [0.006, 0.048, 0.079, 0.105, 0.120, 0.108, 0.100, 0.120, 0.138, 0.177],
                            [0.005, 0.033, 0.062, 0.085, 0.102, 0.086, 0.088, 0.103, 0.144, 0.291]])

    # 0.60 < kc <= 0.70
    mtm_lib[5] = np.matrix([[0.061, 0.169, 0.146, 0.095, 0.106, 0.094, 0.108, 0.085, 0.067, 0.070],
                            [0.023, 0.113, 0.130, 0.114, 0.107, 0.111, 0.102, 0.108, 0.100, 0.092],
                            [0.007, 0.062, 0.105, 0.132, 0.151, 0.126, 0.113, 0.106, 0.097, 0.100],
                            [0.004, 0.026, 0.063, 0.150, 0.189, 0.147, 0.118, 0.108, 0.097, 0.099],
                            [0.002, 0.017, 0.040, 0.098, 0.230, 0.164, 0.130, 0.111, 0.103, 0.106],
                            [0.002, 0.016, 0.040, 0.084, 0.162, 0.179, 0.149, 0.129, 0.119, 0.120],
                            [0.003, 0.018, 0.040, 0.079, 0.142, 0.143, 0.153, 0.140, 0.139, 0.144],
                            [0.002, 0.017, 0.041, 0.079, 0.126, 0.120, 0.135, 0.151, 0.162, 0.167],
                            [0.002, 0.017, 0.034, 0.069, 0.108, 0.106, 0.114, 0.144, 0.191, 0.215],
                            [0.001, 0.012, 0.023, 0.050, 0.083, 0.079, 0.088, 0.118, 0.185, 0.362]])

    # 0.70 < kc <= 0.80
    mtm_lib[6] = np.matrix([[0.049, 0.091, 0.112, 0.070, 0.098, 0.077, 0.105, 0.119, 0.112, 0.168],
                            [0.019, 0.070, 0.090, 0.105, 0.119, 0.113, 0.103, 0.134, 0.121, 0.125],
                            [0.005, 0.028, 0.074, 0.114, 0.130, 0.123, 0.113, 0.118, 0.145, 0.151],
                            [0.001, 0.011, 0.039, 0.102, 0.169, 0.135, 0.123, 0.126, 0.136, 0.156],
                            [0.001, 0.007, 0.021, 0.062, 0.175, 0.143, 0.132, 0.137, 0.157, 0.167],
                            [0.001, 0.007, 0.020, 0.049, 0.117, 0.146, 0.150, 0.157, 0.172, 0.182],
                            [0.000, 0.005, 0.015, 0.047, 0.097, 0.122, 0.151, 0.169, 0.197, 0.197],
                            [0.001, 0.006, 0.016, 0.040, 0.084, 0.098, 0.130, 0.179, 0.224, 0.223],
                            [0.001, 0.005, 0.011, 0.034, 0.067, 0.079, 0.107, 0.161, 0.262, 0.275],
                            [0.000, 0.003, 0.007, 0.022, 0.045, 0.055, 0.074, 0.112, 0.222, 0.459]])

    # 0.80 < kc <= 0.90
    mtm_lib[7] = np.matrix([[0.000, 0.000, 0.077, 0.077, 0.154, 0.077, 0.154, 0.154, 0.077, 0.231],
                            [0.000, 0.043, 0.061, 0.070, 0.061, 0.087, 0.087, 0.217, 0.148, 0.226],
                            [0.000, 0.017, 0.042, 0.073, 0.095, 0.112, 0.120, 0.137, 0.212, 0.193],
                            [0.001, 0.003, 0.015, 0.055, 0.106, 0.091, 0.120, 0.139, 0.219, 0.250],
                            [0.000, 0.002, 0.009, 0.035, 0.097, 0.113, 0.123, 0.155, 0.209, 0.258],
                            [0.000, 0.002, 0.007, 0.028, 0.063, 0.089, 0.123, 0.157, 0.235, 0.295],
                            [0.000, 0.002, 0.005, 0.020, 0.054, 0.069, 0.114, 0.170, 0.260, 0.307],
                            [0.000, 0.001, 0.004, 0.015, 0.043, 0.058, 0.097, 0.174, 0.288, 0.320],
                            [0.000, 0.001, 0.002, 0.011, 0.027, 0.039, 0.071, 0.139, 0.319, 0.390],
                            [0.000, 0.001, 0.001, 0.005, 0.015, 0.024, 0.043, 0.086, 0.225, 0.600]])

    # 0.90 < kc <= 1.00
    mtm_lib[8] = np.matrix([[0.500, 0.250, 0.200, 0.050, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
                            [0.200, 0.500, 0.200, 0.050, 0.050, 0.000, 0.000, 0.000, 0.000, 0.000],
                            [0.000, 0.000, 0.250, 0.000, 0.000, 0.000, 0.250, 0.250, 0.000, 0.250],
                            [0.000, 0.000, 0.000, 0.000, 0.048, 0.000, 0.143, 0.095, 0.190, 0.524],
                            [0.000, 0.000, 0.014, 0.000, 0.027, 0.041, 0.041, 0.233, 0.192, 0.452],
                            [0.000, 0.000, 0.000, 0.008, 0.039, 0.031, 0.078, 0.093, 0.326, 0.425],
                            [0.000, 0.000, 0.000, 0.006, 0.019, 0.019, 0.067, 0.102, 0.254, 0.533],
                            [0.000, 0.000, 0.000, 0.005, 0.012, 0.024, 0.041, 0.106, 0.252, 0.560],
                            [0.000, 0.000, 0.000, 0.001, 0.006, 0.012, 0.031, 0.078, 0.283, 0.589],
                            [0.000, 0.000, 0.000, 0.001, 0.002, 0.004, 0.012, 0.029, 0.134, 0.818]])

    # Determine the appropriate MTM based on the mean monthly kt
    mtm_index = np.digitize([kcm], mtm_states)[0]
    mtm = mtm_lib[mtm_index]

    # Calculate states and step sizes
    min_state = mtm_min[mtm_index]
    max_state = mtm_max[mtm_index]
    step_size = (max_state - min_state) / 10
    states = np.arange(min_state, max_state, step_size)

    kci = kc0
    kc = [kci]
    for i in range(nd - 1):
        mtm_row = np.digitize([kci], states)[0]
        mtm_cum = np.ravel(np.cumsum(mtm[mtm_row - 1, :]))
        new_state = np.digitize([rd[i]], mtm_cum)[0] + 1

        if new_state > 10:
            new_state = 10

        # Calculate interpolation factor
        if new_state == 1:
            k_interp = (rd[i] / mtm_cum[new_state - 1]) * 0.1
        else:
            k_interp = (rd[i] - mtm_cum[new_state - 2]) / (mtm_cum[new_state - 1] - mtm_cum[new_state - 2]) * 0.1

        kci = k_interp + (new_state - 1) * 0.1
        kc.append(kci)

    return kc


@jit((float64[:], float64[:], float64, float64, float64[:], float64, float64, int64), cache=True, nopython=True)
def _generate_hourly_kt_over_day(elevation, htime, kt_day, kc_day, kt_cls, sunrise, sunset, max_iter):

    phi = 0.148 + 2.356 * kt_day - 5.195 * kt_day ** 2 + 3.758 * kt_day ** 3
    sigma = 0.32 * np.exp(-50 * (kt_day - 0.4) ** 2) + 0.002
    sigma_prime = sigma * (1 - phi ** 2) ** 0.5

    kt = np.zeros(len(elevation))
    y = np.zeros(len(elevation))

    for time, h_sun, kcs in zip(htime, elevation, kt_cls):

        if time + 0.5 > sunrise and time - 0.5 < sunset:

            # Average clearness index (MeteoNorm version)
            ktm = kc_day * kcs

            # Generate new kt only if greater than 0 and less than clear sky kt
            kti = yi = -1
            _iter = 0
            while (kti < 0) or (kti > kcs):
                r = np.random.normal(loc=0, scale=sigma_prime)
                yi = 2 * phi * y[int(time) - 1] + r  # MeteoNorm version
                kti = ktm + yi

                # Iteration control
                _iter = _iter + 1
                if _iter > max_iter:
                    if kti < 0:
                        kti = 0
                    if kti > kcs:
                        kti = kcs

                if kti > 0.8 and h_sun < 10:
                    kti = 0.8

            kt[int(time)] = kti
            y[int(time)] = yi

    return kt


if __name__ == "__main__":
    from pvlib.location import Location
    from utils.sys.timer import Timer
    kcm_main = [0.61, 0.6, 0.605, 0.595, 0.608, 0.602, 0.61, 0.6, 0.593, 0.598, 0.601, 0.602]
    kc0_main = kcm_main
    # test = _generate_daily_kc(0.5, 0.5, 31)
    # print(np.mean(test))
    loc = Location(latitude=5, longitude=-70, altitude=100)
    kc_main = generate_daily_kc_sequence(kcm_main, 2018, tz=loc.tz, tolerance=0.01)
    print([np.mean(kc) for kc in kc_main])
    print(np.mean(kcm_main))
    with Timer() as t:
        cls_r = generate_daily_clear_sky_sequence(loc, "30min", 2018)
    print("spent time: %s" % t)
    toa_r = generate_daily_toa_sequence(loc, "30min", 2018)
    kt_main = kc_main * cls_r / toa_r
    #
    with Timer() as t:
        for p in range(30):
            kc_main_test = generate_daily_kc_sequence_over_month(kcm_main, kc0_main, 2, 2018, tz=loc.tz, tolerance=0.01)
            # hourly_ghi = generate_hourly_ghi_sequence(kt_main, kc_main, toa_r, loc, "30min", 2018, 0.05)
    print("spent time: %s" % t)
    #
    # original_ghi = kcm_main[1] * np.sum(cls_r[cls_r.index.month == 2])
    # intermediate_ghi = np.sum(cls_r[cls_r.index.month == 2] * kc_main[kc_main.index.month == 2])
    # final_ghi = np.sum(hourly_ghi[hourly_ghi.index.month == 2])
    #
    # print("Original GHI: %.3f" % original_ghi)
    # print("Intermediate GHI: %.3f" % intermediate_ghi)
    # print("Final GHI: %.3f" % final_ghi)
    # print("relative : %.2f" % ((original_ghi - final_ghi)/original_ghi))
