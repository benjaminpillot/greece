# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

__version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


from greece.utils.check import *
from pandas import DatetimeIndex
from greece.tmstools import TimeSeries
from greece.gistools.coordinates import LocationBase, Location
from pysolar import constants
from numpy import array, asarray, concatenate, floor, pi, sin, cos, tan, arcsin, arctan, arctan2


# Constants for sun position calculation
L0, L1, L2, L3, L4, L5 = asarray(constants.heliocentric_longitude_coeffs[0]), asarray(
    constants.heliocentric_longitude_coeffs[1]), asarray(constants.heliocentric_longitude_coeffs[2]), \
                         asarray(constants.heliocentric_longitude_coeffs[3]), asarray(
    constants.heliocentric_longitude_coeffs[4]), asarray(constants.heliocentric_longitude_coeffs[5][0])
B0, B1 = asarray(constants.heliocentric_latitude_coeffs[0]), asarray(constants.heliocentric_latitude_coeffs[1])
R0, R1, R2, R3, R4 = asarray(constants.sun_earth_distance_coeffs[0]), asarray(constants.sun_earth_distance_coeffs[1]),\
                     asarray(constants.sun_earth_distance_coeffs[2]), asarray(constants.sun_earth_distance_coeffs[3]),\
                     asarray(constants.sun_earth_distance_coeffs[4][0])
ABERRATION_SIN_TERMS = asarray(constants.aberration_sin_terms)
NUTATION_TERMS = asarray(constants.nutation_coefficients)


class Surface(metaclass=CheckedMeta):
    """ Surface class

    Store surface property angles (azimuth and slope)
    for further solar computation
    """
    azimuth = BoundedFloat(min=0, max=360)
    slope = BoundedFloat(min=0, max=90)

    def __init__(self, azimuth: float, slope: float):
        """ Build Surface class instance

        :type azimuth: float
        :param slope: surface slope (0-90°)
        :param azimuth: surface azimuth (0-360°)
        :type slope: float
        """
        self.azimuth = azimuth
        self.slope = slope


class SunPosition:
    """ SunPosition class

    Compute and store sun position angles (azimuth,
    elevation) computed with respect to location and
    time using the NREL-based algorithm and the ESRA
    refraction correction
    """

    elevation = protected_property("elevation")
    azimuth = protected_property("azimuth")
    time = protected_property("time")
    location = protected_property("location")

    def __init__(self, time, location: LocationBase):
        """

        :param time:
        :type time:
        :param location:
        :type location:
        """
        check_type(time, Collection, location, LocationBase)

        self._location = location
        self._elevation = TimeSeries(time, dtype='object')
        self._time = self._elevation.time

        # Compute sun angles
        if isinstance(self._location, Location):
            self._sun_position = _sun_position(self._time, self._location.longitude, self._location.latitude,
                                               self._location.altitude)
        else:
            self._sun_position = _sun_position(self._time, asarray(self._location.longitude),
                                               asarray(self._location.latitude), asarray(self._location.altitude))
            self._sun_position["elevation"] = list(self._sun_position["elevation"])
            self._sun_position["apparent_elevation"] = list(self._sun_position["apparent_elevation"])
            self._sun_position["azimuth"] = list(self._sun_position["azimuth"])

        # Store sun angles in corresponding time series
        self._elevation[:] = self._sun_position["elevation"]
        self._apparent_elevation = TimeSeries(time, self._sun_position["apparent_elevation"])
        self._azimuth = TimeSeries(time, self._sun_position["azimuth"])
        self._zenith = 90 - self._elevation
        self._apparent_zenith = 90 - self._apparent_elevation


def _sun_position(time: DatetimeIndex, longitude, latitude, altitude):
    """ Compute sun position angles

    :param time: DatetimeIndex
    :type time:
    :param longitude:
    :type longitude: array or float
    :param latitude:
    :type latitude: array or float
    :param altitude:
    :type altitude: array or float
    :return:
    :rtype: dictionary
    """

    def set_to_range(param):
        param = param - 360 * floor(param/360)
        param[param < 0] = param[param < 0] + 360

        return param

    def julian():
        delta_t = 0  # 33.184
        julian_day = array(time.to_julian_date()).reshape(time.size, 1)
        julian_ephemeris_day = julian_day + delta_t/86400
        julian_century = (julian_day - 2451545)/36525
        julian_ephemeris_century = (julian_ephemeris_day - 2451545)/36525
        julian_ephemeris_millennium = julian_ephemeris_century/10
        return julian_day, julian_ephemeris_day, julian_century, julian_ephemeris_century, julian_ephemeris_millennium

    def earth_heliocentric_position(julian_ephemeris_millennium):

        # Earth heliocentric longitude
        l0 = (L0[:, 0] * cos(L0[:, 1] + L0[:, 2] * julian_ephemeris_millennium)).sum(1, keepdims=True)
        l1 = (L1[:, 0] * cos(L1[:, 1] + L1[:, 2] * julian_ephemeris_millennium)).sum(1, keepdims=True)
        l2 = (L2[:, 0] * cos(L2[:, 1] + L2[:, 2] * julian_ephemeris_millennium)).sum(1, keepdims=True)
        l3 = (L3[:, 0] * cos(L3[:, 1] + L3[:, 2] * julian_ephemeris_millennium)).sum(1, keepdims=True)
        l4 = (L4[:, 0] * cos(L4[:, 1] + L4[:, 2] * julian_ephemeris_millennium)).sum(1, keepdims=True)
        l5 = (L5[0] * cos(L5[1] + L5[2] * julian_ephemeris_millennium)).sum(1, keepdims=True)

        earth_heliocentric_longitude = set_to_range((l0 + l1 * julian_ephemeris_millennium +
                                                     l2 * julian_ephemeris_millennium**2 + l3
                                                     * julian_ephemeris_millennium**3 + l4 *
                                                     julian_ephemeris_millennium**4 + l5 *
                                                     julian_ephemeris_millennium**5)/1e8 * 180/pi)

        # Earth heliocentric latitude
        l0 = (B0[:, 0] * cos(B0[:, 1] + B0[:, 2] * julian_ephemeris_millennium)).sum(1, keepdims=True)
        l1 = (B1[:, 0] * cos(B1[:, 1] + B1[:, 2] * julian_ephemeris_millennium)).sum(1, keepdims=True)

        earth_heliocentric_latitude = set_to_range((l0 + l1 * julian_ephemeris_millennium)/1e8 * 180/pi)

        # Earth heliocentric radius
        l0 = (R0[:, 0] * cos(R0[:, 1] + R0[:, 2] * julian_ephemeris_millennium)).sum(1, keepdims=True)
        l1 = (R1[:, 0] * cos(R1[:, 1] + R1[:, 2] * julian_ephemeris_millennium)).sum(1, keepdims=True)
        l2 = (R2[:, 0] * cos(R2[:, 1] + R2[:, 2] * julian_ephemeris_millennium)).sum(1, keepdims=True)
        l3 = (R3[:, 0] * cos(R3[:, 1] + R3[:, 2] * julian_ephemeris_millennium)).sum(1, keepdims=True)
        l4 = (R4[0] * cos(R4[1] + R4[2] * julian_ephemeris_millennium)).sum(1, keepdims=True)

        earth_heliocentric_radius = (l0 + l1 * julian_ephemeris_millennium + l2 *
                                     julian_ephemeris_millennium**2 + l3 *
                                     julian_ephemeris_millennium**3 + l4 *
                                     julian_ephemeris_millennium**4)/1e8

        return earth_heliocentric_longitude, earth_heliocentric_latitude, earth_heliocentric_radius

    def sun_geocentric_position(earth_heliocentric_longitude, earth_heliocentric_latitude):
        sun_geocentric_longitude = set_to_range(earth_heliocentric_longitude + 180)
        sun_geocentric_latitude = set_to_range(-earth_heliocentric_latitude)
        return sun_geocentric_longitude, sun_geocentric_latitude

    def nutation(julian_ephemeris_century):

        # Mean elongation of the moon from the sun
        x0 = (1/189474) * julian_ephemeris_century**3 - 0.0019142 * julian_ephemeris_century**2 + \
            445267.11148 * julian_ephemeris_century + 297.85036

        # Mean anomaly of the sun
        x1 = -(1/300000) * julian_ephemeris_century**3 - 0.0001603 * julian_ephemeris_century**2 + \
            35999.05034 * julian_ephemeris_century + 357.52772

        # Mean anomaly of the moon
        x2 = (1/56250) * julian_ephemeris_century**3 + 0.0086972 * julian_ephemeris_century**2 + \
            477198.867398 * julian_ephemeris_century + 134.96298

        # Moon argument of latitude
        x3 = (1/327270) * julian_ephemeris_century**3 - 0.0036825 * julian_ephemeris_century**2 + \
            483202.017538 * julian_ephemeris_century + 93.27191

        # Longitude of the ascending node of the moon's mean orbit
        x4 = (1/450000) * julian_ephemeris_century**3 + 0.0020708 * julian_ephemeris_century**2 - \
            1934.136261 * julian_ephemeris_century + 125.04452

        xi = concatenate((x0, x1, x2, x3, x4), axis=1).transpose()

        tabulated_argument = (ABERRATION_SIN_TERMS.dot(xi) * pi/180).transpose()

        delta_longitude = (NUTATION_TERMS[:, 0] + NUTATION_TERMS[:, 1] * julian_ephemeris_century) * sin(
            tabulated_argument)

        delta_obliquity = (NUTATION_TERMS[:, 2] + NUTATION_TERMS[:, 3] * julian_ephemeris_century) * cos(
            tabulated_argument)

        nutation_longitude = delta_longitude.sum(1, keepdims=True)/36000000
        nutation_obliquity = delta_obliquity.sum(1, keepdims=True)/36000000

        return nutation_longitude, nutation_obliquity

    def true_obliquity_calculation(julian_ephemeris_millennium, nutation_obliquity):
        u = julian_ephemeris_millennium/10
        mean_obliquity = 2.45 * u**10 + 5.79 * u**9 + 27.87 * u**8 + 7.12 * u**7 - 39.05 * u**6 - 249.67 * u**5 - \
            51.38 * u**4 + 1999.25 * u**3 - 1.55 * u**2 - 4680.93 * u + 84381.448
        return mean_obliquity/3600 + nutation_obliquity

    def aberration_correction(earth_heliocentric_radius):
        return -20.4898/(3600 * earth_heliocentric_radius)

    def apparent_sun_longitude_calculation(sun_geocentric_longitude, nutation_longitude, aberration):
        return sun_geocentric_longitude + nutation_longitude + aberration

    def apparent_sidereal_time_at_greenwich_calculation(julian_day, julian_century, nutation_longitude, true_obliquity):
        mean_sidereal_time = set_to_range(280.46061837 + 360.98564736629 * (julian_day - 2451545) + 0.000387933 *
                                          julian_century**2 - (julian_century**3)/38710000)
        return mean_sidereal_time + nutation_longitude * cos(true_obliquity * pi/180)

    def sun_right_ascension_calculation(apparent_sun_longitude, true_obliquity, sun_geocentric_latitude):
        sun_right_ascension = arctan2(sin(apparent_sun_longitude * pi/180) *
                                      cos(true_obliquity * pi/180) -
                                      tan(sun_geocentric_latitude * pi/180) *
                                      sin(true_obliquity * pi/180), cos(apparent_sun_longitude *
                                                                        pi/180)) * 180/pi
        return set_to_range(sun_right_ascension)

    def sun_geocentric_declination_calculation(apparent_sun_longitude, true_obliquity, sun_geocentric_latitude):
        return arcsin(sin(sun_geocentric_latitude * pi/180) * cos(true_obliquity * pi/180) +
                      cos(sun_geocentric_latitude * pi/180) * sin(true_obliquity * pi/180) *
                      sin(apparent_sun_longitude * pi/180)) * 180/pi

    def observer_local_hour_calculation(apparent_sidereal_time_at_greenwich, sun_right_ascension):
        return set_to_range(apparent_sidereal_time_at_greenwich + longitude - sun_right_ascension)

    def topocentric_sun_position(earth_heliocentric_radius, observer_local_hour, sun_right_ascension,
                                 sun_geocentric_declination):
        equatorial_horizontal_parallax = 8.794/(3600 * earth_heliocentric_radius)
        u = arctan(0.99664719 * tan(latitude * pi/180))
        x = cos(u) + (altitude/6378140) * cos(latitude * pi/180)
        y = 0.99664719 * sin(u) + (altitude/6378140) * sin(latitude * pi/180)

        right_ascension_parallax = arctan2(-x * sin(equatorial_horizontal_parallax * pi/180) * sin(
            observer_local_hour * pi/180), cos(sun_geocentric_declination * pi/180) - x * sin(
            equatorial_horizontal_parallax * pi/180) * cos(observer_local_hour * pi/180)) * 180/pi
        topocentric_sun_right_ascension = sun_right_ascension + right_ascension_parallax
        topocentric_sun_declination = arctan2((sin(sun_geocentric_declination * pi/180) - y * sin(
            equatorial_horizontal_parallax * pi/180)) * cos(right_ascension_parallax * pi/180),
                                              cos(sun_geocentric_declination * pi/180) - x * sin(
                                                  equatorial_horizontal_parallax * pi/180) * cos(observer_local_hour
                                                                                                 * pi/180)) * 180/pi

        return right_ascension_parallax, topocentric_sun_right_ascension, topocentric_sun_declination

    def topocentric_local_hour_calculation(observer_local_hour, right_ascension_parallax):
        return observer_local_hour - right_ascension_parallax

    def topocentric_zenith_angle_calculation(topocentric_sun_declination, topocentric_local_hour):

        # Topocentric sun elevation without atmospheric refraction
        elevation = arcsin(sin(latitude * pi/180) * sin(topocentric_sun_declination * pi/180) +
                           cos(latitude * pi/180) * cos(topocentric_sun_declination * pi/180) * cos(
                               topocentric_local_hour * pi/180)) * 180/pi
        elevation = elevation.squeeze(axis=1)

        # Atmospheric refraction according to Rigollier et al. (2000)
        refraction_correction = 0.061359 * (180/pi) * (0.1594 + 1.1230 * (pi/180) * elevation + 0.065656 * (
            pi/180)**2 * elevation**2)/(1 + 28.9344 * (pi/180) * elevation + 277.3971 * (pi/180)**2 * elevation**2)
        apparent_elevation = elevation + refraction_correction

        # Azimuth
        azimuth = 180 + arctan2(sin(topocentric_local_hour * pi/180), cos(topocentric_local_hour * pi/180) * sin(
            latitude * pi/180) - tan(topocentric_sun_declination * pi/180) * cos(latitude * pi/180)) * 180/pi
        azimuth = set_to_range(azimuth.squeeze(axis=1))

        return {"elevation": elevation, "apparent_elevation": apparent_elevation, "azimuth": azimuth}

    _julian_day, _julian_ephemeris_day, _julian_century, _julian_ephemeris_century, _julian_ephemeris_millennium = \
        julian()
    _earth_heliocentric_longitude, _earth_heliocentric_latitude, _earth_heliocentric_radius = \
        earth_heliocentric_position(_julian_ephemeris_millennium)
    _sun_geocentric_longitude, _sun_geocentric_latitude = sun_geocentric_position(_earth_heliocentric_longitude,
                                                                                  _earth_heliocentric_latitude)
    _nutation_longitude, _nutation_obliquity = nutation(_julian_ephemeris_century)
    _true_obliquity = true_obliquity_calculation(_julian_ephemeris_millennium, _nutation_obliquity)
    _aberration = aberration_correction(_earth_heliocentric_radius)
    _apparent_sun_longitude = apparent_sun_longitude_calculation(_sun_geocentric_longitude, _nutation_longitude,
                                                                 _aberration)
    _apparent_sidereal_time_at_greenwich = apparent_sidereal_time_at_greenwich_calculation(_julian_day,
                                                                                           _julian_century,
                                                                                           _nutation_longitude,
                                                                                           _true_obliquity)
    _sun_right_ascension = sun_right_ascension_calculation(_apparent_sun_longitude, _true_obliquity,
                                                           _sun_geocentric_latitude)
    _sun_geocentric_declination = sun_geocentric_declination_calculation(_apparent_sun_longitude, _true_obliquity,
                                                                         _sun_geocentric_latitude)
    _observer_local_hour = observer_local_hour_calculation(_apparent_sidereal_time_at_greenwich, _sun_right_ascension)
    _right_ascension_parallax, _topocentric_sun_right_ascension, _topocentric_sun_declination = \
        topocentric_sun_position(_earth_heliocentric_radius, _observer_local_hour, _sun_right_ascension,
                                 _sun_geocentric_declination)
    _topocentric_local_hour = topocentric_local_hour_calculation(_observer_local_hour, _right_ascension_parallax)

    return topocentric_zenith_angle_calculation(_topocentric_sun_declination, _topocentric_local_hour)


# mtm_states = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
# mtm_min = [0.031, 0.058, 0.051, 0.052, 0.028, 0.053, 0.044, 0.085, 0.010, 0.319]
# mtm_max = [0.705, 0.694, 0.753, 0.753, 0.807, 0.856, 0.818, 0.846, 0.842, 0.865]
#
# # kt <= 0.30
# mtm_lib[0] = np.matrix([[0.229, 0.333, 0.208, 0.042, 0.083, 0.042, 0.042, 0.021, 0.000, 0.000],
#                         [0.167, 0.319, 0.194, 0.139, 0.097, 0.028, 0.042, 0.000, 0.014, 0.000],
#                         [0.250, 0.250, 0.091, 0.136, 0.091, 0.046, 0.046, 0.023, 0.068, 0.000],
#                         [0.158, 0.237, 0.158, 0.263, 0.026, 0.053, 0.079, 0.026, 0.000, 0.000],
#                         [0.211, 0.053, 0.211, 0.158, 0.053, 0.053, 0.158, 0.105, 0.000, 0.000],
#                         [0.125, 0.125, 0.250, 0.188, 0.063, 0.125, 0.000, 0.125, 0.000, 0.000],
#                         [0.040, 0.240, 0.080, 0.120, 0.080, 0.080, 0.120, 0.120, 0.080, 0.040],
#                         [0.000, 0.250, 0.000, 0.125, 0.000, 0.125, 0.125, 0.250, 0.063, 0.063],
#                         [0.000, 0.250, 0.000, 0.125, 0.250, 0.000, 0.250, 0.000, 0.000, 0.125],
#                         [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.500, 0.250, 0.000, 0.250]])
#
# # 0.30 < kt <= 0.35
# mtm_lib[1] = np.matrix([[0.000, 0.000, 0.091, 0.000, 0.364, 0.091, 0.182, 0.000, 0.273, 0.000],
#                         [0.118, 0.118, 0.176, 0.118, 0.059, 0.118, 0.176, 0.059, 0.059, 0.000],
#                         [0.067, 0.267, 0.067, 0.200, 0.067, 0.000, 0.133, 0.133, 0.000, 0.067],
#                         [0.118, 0.235, 0.000, 0.235, 0.059, 0.176, 0.118, 0.000, 0.059, 0.000],
#                         [0.077, 0.154, 0.308, 0.077, 0.154, 0.077, 0.000, 0.077, 0.077, 0.000],
#                         [0.083, 0.000, 0.167, 0.250, 0.083, 0.167, 0.000, 0.083, 0.167, 0.000],
#                         [0.222, 0.222, 0.000, 0.111, 0.111, 0.000, 0.111, 0.222, 0.000, 0.000],
#                         [0.091, 0.182, 0.273, 0.000, 0.091, 0.273, 0.000, 0.091, 0.000, 0.000],
#                         [0.111, 0.111, 0.111, 0.222, 0.000, 0.000, 0.000, 0.222, 0.111, 0.111],
#                         [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.500, 0.000, 0.000, 0.500]])
#
# # 0.35 < kt <= 0.40
# mtm_lib[2] = np.matrix([[0.206, 0.088, 0.176, 0.176, 0.088, 0.029, 0.176, 0.029, 0.029, 0.000],
#                         [0.120, 0.100, 0.140, 0.160, 0.120, 0.220, 0.100, 0.000, 0.020, 0.020],
#                         [0.077, 0.123, 0.185, 0.123, 0.077, 0.139, 0.092, 0.123, 0.061, 0.000],
#                         [0.048, 0.111, 0.095, 0.206, 0.206, 0.190, 0.095, 0.048, 0.000, 0.000],
#                         [0.059, 0.137, 0.118, 0.137, 0.098, 0.118, 0.118, 0.157, 0.059, 0.000],
#                         [0.014, 0.097, 0.139, 0.153, 0.125, 0.139, 0.208, 0.056, 0.042, 0.028],
#                         [0.073, 0.101, 0.116, 0.145, 0.087, 0.159, 0.203, 0.087, 0.029, 0.000],
#                         [0.019, 0.037, 0.111, 0.056, 0.074, 0.111, 0.185, 0.296, 0.074, 0.037],
#                         [0.035, 0.069, 0.035, 0.000, 0.035, 0.103, 0.172, 0.138, 0.379, 0.035],
#                         [0.000, 0.167, 0.167, 0.000, 0.167, 0.000, 0.000, 0.333, 0.000, 0.167]])
#
# # 0.40 < kt <= 0.45
# mtm_lib[3] = np.matrix([[0.167, 0.167, 0.167, 0.000, 0.083, 0.125, 0.000, 0.167, 0.125, 0.000],
#                         [0.117, 0.117, 0.150, 0.117, 0.083, 0.117, 0.200, 0.067, 0.017, 0.017],
#                         [0.049, 0.085, 0.134, 0.158, 0.098, 0.110, 0.134, 0.134, 0.061, 0.037],
#                         [0.039, 0.090, 0.141, 0.141, 0.167, 0.141, 0.090, 0.141, 0.039, 0.013],
#                         [0.009, 0.139, 0.074, 0.093, 0.194, 0.139, 0.167, 0.093, 0.074, 0.019],
#                         [0.036, 0.018, 0.117, 0.099, 0.144, 0.180, 0.180, 0.117, 0.072, 0.036],
#                         [0.000, 0.046, 0.061, 0.061, 0.136, 0.159, 0.273, 0.167, 0.098, 0.000],
#                         [0.016, 0.056, 0.080, 0.128, 0.104, 0.080, 0.160, 0.208, 0.136, 0.032],
#                         [0.011, 0.053, 0.021, 0.043, 0.128, 0.096, 0.074, 0.223, 0.277, 0.074],
#                         [0.000, 0.074, 0.037, 0.000, 0.074, 0.074, 0.074, 0.074, 0.333, 0.259]])
#
# # 0.45 < kt <= 0.50
# mtm_lib[4] = np.matrix([[0.120, 0.200, 0.160, 0.120, 0.120, 0.120, 0.080, 0.000, 0.040, 0.040],
#                         [0.100, 0.080, 0.120, 0.140, 0.140, 0.200, 0.180, 0.040, 0.000, 0.000],
#                         [0.046, 0.114, 0.068, 0.171, 0.125, 0.171, 0.080, 0.159, 0.057, 0.011],
#                         [0.015, 0.061, 0.084, 0.099, 0.191, 0.153, 0.153, 0.115, 0.115, 0.015],
#                         [0.024, 0.030, 0.098, 0.098, 0.165, 0.195, 0.195, 0.140, 0.043, 0.012],
#                         [0.015, 0.026, 0.062, 0.124, 0.144, 0.170, 0.170, 0.222, 0.062, 0.005],
#                         [0.000, 0.013, 0.045, 0.108, 0.112, 0.175, 0.188, 0.224, 0.117, 0.018],
#                         [0.008, 0.023, 0.054, 0.066, 0.093, 0.125, 0.191, 0.253, 0.183, 0.004],
#                         [0.006, 0.022, 0.061, 0.033, 0.067, 0.083, 0.139, 0.222, 0.322, 0.044],
#                         [0.000, 0.046, 0.091, 0.091, 0.046, 0.046, 0.136, 0.091, 0.273, 0.182]])
#
# # 0.50 < kt <= 0.55
# mtm_lib[5] = np.matrix([[0.250, 0.179, 0.107, 0.107, 0.143, 0.071, 0.107, 0.036, 0.000, 0.000],
#                         [0.133, 0.022, 0.089, 0.111, 0.156, 0.178, 0.111, 0.133, 0.067, 0.000],
#                         [0.064, 0.048, 0.143, 0.048, 0.175, 0.143, 0.206, 0.095, 0.079, 0.000],
#                         [0.000, 0.022, 0.078, 0.111, 0.156, 0.156, 0.244, 0.167, 0.044, 0.022],
#                         [0.016, 0.027, 0.037, 0.069, 0.160, 0.219, 0.230, 0.160, 0.075, 0.005],
#                         [0.013, 0.025, 0.030, 0.093, 0.144, 0.202, 0.215, 0.219, 0.055, 0.004],
#                         [0.006, 0.041, 0.035, 0.064, 0.090, 0.180, 0.337, 0.192, 0.049, 0.006],
#                         [0.012, 0.021, 0.029, 0.035, 0.132, 0.123, 0.184, 0.371, 0.082, 0.012],
#                         [0.008, 0.016, 0.016, 0.024, 0.071, 0.103, 0.159, 0.270, 0.309, 0.024],
#                         [0.000, 0.000, 0.000, 0.000, 0.059, 0.000, 0.059, 0.294, 0.412, 0.176]])
#
# # 0.55 < kt <= 0.60
# mtm_lib[6] = np.matrix([[0.217, 0.087, 0.000, 0.174, 0.130, 0.087, 0.087, 0.130, 0.087, 0.000],
#                         [0.026, 0.079, 0.132, 0.079, 0.026, 0.158, 0.158, 0.132, 0.158, 0.053],
#                         [0.020, 0.020, 0.020, 0.040, 0.160, 0.180, 0.160, 0.200, 0.100, 0.100],
#                         [0.025, 0.013, 0.038, 0.076, 0.076, 0.139, 0.139, 0.266, 0.215, 0.013],
#                         [0.030, 0.030, 0.050, 0.020, 0.091, 0.131, 0.162, 0.283, 0.131, 0.071],
#                         [0.006, 0.006, 0.013, 0.057, 0.057, 0.121, 0.204, 0.287, 0.185, 0.064],
#                         [0.004, 0.026, 0.037, 0.030, 0.093, 0.107, 0.193, 0.307, 0.167, 0.037],
#                         [0.011, 0.009, 0.014, 0.042, 0.041, 0.071, 0.152, 0.418, 0.203, 0.041],
#                         [0.012, 0.022, 0.022, 0.038, 0.019, 0.050, 0.113, 0.281, 0.360, 0.084],
#                         [0.008, 0.024, 0.039, 0.039, 0.063, 0.039, 0.118, 0.118, 0.284, 0.268]])
#
# # 0.60 < kt <= 0.65
# mtm_lib[7] = np.matrix([[0.067, 0.133, 0.133, 0.067, 0.067, 0.200, 0.133, 0.133, 0.067, 0.000],
#                         [0.118, 0.059, 0.059, 0.059, 0.059, 0.118, 0.118, 0.235, 0.118, 0.059],
#                         [0.000, 0.024, 0.024, 0.049, 0.146, 0.073, 0.195, 0.244, 0.195, 0.049],
#                         [0.026, 0.000, 0.026, 0.026, 0.053, 0.184, 0.263, 0.184, 0.237, 0.000],
#                         [0.014, 0.000, 0.042, 0.056, 0.069, 0.097, 0.139, 0.306, 0.278, 0.000],
#                         [0.009, 0.009, 0.052, 0.069, 0.052, 0.112, 0.215, 0.285, 0.138, 0.060],
#                         [0.009, 0.009, 0.026, 0.017, 0.094, 0.099, 0.232, 0.283, 0.210, 0.021],
#                         [0.010, 0.014, 0.016, 0.019, 0.027, 0.062, 0.163, 0.467, 0.202, 0.019],
#                         [0.004, 0.007, 0.031, 0.017, 0.033, 0.050, 0.086, 0.252, 0.469, 0.050],
#                         [0.000, 0.000, 0.015, 0.046, 0.031, 0.046, 0.077, 0.123, 0.446, 0.215]])
#
# # 0.65 < kt <= 0.70
# mtm_lib[8] = np.matrix([[0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 1.000, 0.000],
#                         [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 1.000, 0.000],
#                         [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.250, 0.250, 0.500, 0.000],
#                         [0.000, 0.000, 0.000, 0.000, 0.250, 0.000, 0.000, 0.375, 0.250, 0.125],
#                         [0.000, 0.000, 0.000, 0.083, 0.000, 0.167, 0.167, 0.250, 0.333, 0.000],
#                         [0.000, 0.000, 0.042, 0.042, 0.042, 0.083, 0.083, 0.292, 0.292, 0.125],
#                         [0.000, 0.000, 0.032, 0.000, 0.000, 0.032, 0.129, 0.387, 0.355, 0.065],
#                         [0.000, 0.000, 0.000, 0.038, 0.038, 0.075, 0.047, 0.340, 0.415, 0.047],
#                         [0.004, 0.004, 0.007, 0.007, 0.011, 0.030, 0.052, 0.141, 0.654, 0.089],
#                         [0.000, 0.000, 0.000, 0.000, 0.061, 0.061, 0.030, 0.030, 0.349, 0.470]])
#
# # kt > 0.70
# mtm_lib[9] = np.matrix([[0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 1.000, 0.000],
#                         [0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100, 0.100],
#                         [0.000, 0.000, 0.000, 0.250, 0.000, 0.000, 0.000, 0.500, 0.250, 0.000],
#                         [0.000, 0.000, 0.143, 0.143, 0.000, 0.143, 0.143, 0.429, 0.000, 0.000],
#                         [0.000, 0.000, 0.000, 0.200, 0.000, 0.000, 0.200, 0.400, 0.200, 0.000],
#                         [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.222, 0.444, 0.333, 0.000],
#                         [0.000, 0.000, 0.000, 0.000, 0.080, 0.080, 0.080, 0.480, 0.240, 0.040],
#                         [0.000, 0.000, 0.027, 0.009, 0.027, 0.018, 0.135, 0.523, 0.252, 0.009],
#                         [0.000, 0.000, 0.000, 0.022, 0.000, 0.043, 0.043, 0.326, 0.511, 0.054],
#                         [0.000, 0.000, 0.000, 0.143, 0.000, 0.000, 0.000, 0.143, 0.714, 0.000]])
#
# Generate daily clearness indices for nd days
# kti = kc0_main
# kt = [kti]
# for i in range(nd - 1):
# mtm_row = np.digitize([kti], states, right=True)[0]
# mtm_cum = np.ravel(np.cumsum(mtm[mtm_row - 1, :]))
# new_state = np.digitize([rd[i]], mtm_cum)[0] + 1
#
# if new_state > 10:
#     new_state = 10
#
# # Calculate interpolation factor
# if new_state == 1:
#     k_interp = rd[i] / mtm_cum[new_state - 1]
# else:
#     k_interp = (rd[i] - mtm_cum[new_state - 2]) / (mtm_cum[new_state - 1] - mtm_cum[new_state - 2])
#
# kti = states[new_state - 1] + k_interp * step_size
# kt.append(kti)


# def _generate_hourly_kt(daily_kt, daily_kc, sunrise, sunset, elevation, kcs, max_iter=10):
#     """
#     Generates a sequence of synthetic hourly clearness indices (kt) using the mean daily clearness
#     index (daily_kt) as the input. The algorithm is based on the method by Aguiar et al in the paper:
#
#     R. Aguiar and M. Collares-Pereira, "TAG: A time-dependent, autoregressive Gaussian model
#       for generating synthetic hourly radiation", Solar Energy, vol. 49, 167-174, 1992
#
#     :param daily_kt: TimeSeries of daily kt values
#     :param daily_kc: Timeseries of daily kc_main values
#     :param sunrise:
#     :param sunset:
#     :param elevation:
#     :param kcs: clearsky clearness index
#     :param max_iter: maximum number of iterations
#     """
#
#     # Autocorrelation coefficient
#     # phi = 0.38 + 0.06 * np.cos(7.4 * daily_kt - 2.5)
#     phi = 0.148 + 2.356 * daily_kt - 5.195 * daily_kt ** 2 + 3.758 * daily_kt ** 3
#     sigma = 0.32 * np.exp(-50 * (daily_kt - 0.4) ** 2) + 0.002
#     sigma_prime = sigma * (1 - phi ** 2) ** 0.5
#
#     # Calculate algorithm constants
#     lmbda = -0.19 + 1.12 * daily_kt + 0.24 * np.exp(-8 * daily_kt)
#     eta = 0.32 - 1.6 * (daily_kt - 0.5) ** 2
#     kappa = 0.19 + 2.27 * daily_kt ** 2 - 2.51 * daily_kt ** 3
#     aa = 0.14 * np.exp(-20 * (daily_kt - 0.35) ** 2)
#     bb = 3 * (daily_kt - 0.45) ** 2 + 16 * daily_kt ** 5
#
#     # Generate kt for each solar hour
#     kt = []
#     y = []

# for n, time in enumerate(elevation.index):
#
#     if time + Timedelta("30min") > sunrise[n] and time - Timedelta("30min") < sunset[n]:
#
#         day = Timestamp(time.year, time.month, time.day)
#
#         # Average clearness index (MeteoNorm version)
#         # ktm = daily_kt[day]
#         ktm = daily_kc[day] * kcs[n]
#         # ktm = lmbda[day] + eta[day] * np.exp(-kappa[day] / np.sin(np.pi * elevation[n] / 180))
#
#         # Standard deviation
#         # sigma = aa[day] * np.exp(bb[day] * (1 - np.sin(np.pi * elevation[n] / 180)))
#
#         # Generate new kt only if greater than 0 and less than clear sky kt
#         kti = -1
#         _iter = 0
#         while (kti < 0) or (kti > kcs[n]):
#             # z = np.random.rand()
#             # r = sigma * (z ** 0.135 - (1 - z) ** 0.135) / 0.1975
#             r = np.random.normal(loc=0, scale=sigma_prime[day])
#             yi = 2 * phi[day] * y[time.hour - 1] + r  # MeteoNorm version
#             # yi = phi[day] * y[time.hour - 2] + r
#             # yi = phi[day] * y[time.hour - 1] + r
#             # kti = ktm + sigma * yi
#             kti = ktm + yi
#
#             # Iteration control
#             _iter = _iter + 1
#             if _iter > max_iter:
#                 if kti < 0:
#                     kti = 0
#                 if kti > kcs[n]:
#                     kti = kcs[n]
#
#             if kti > 0.8 and elevation[n] < 10:
#                 kti = 0.8
#
#         kt.append(kti)
#         y.append(yi)
#     else:
#         # For non-sunlight hours, set kt to zero
#         kt.append(0)
#         y.append(0)
#
# return kt
