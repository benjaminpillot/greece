# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""
from numpy import isnan
from pvlib.location import Location
from gistools.exceptions import GeoLayerError

__version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


def get_location_from_polygon_layer(polygon_layer, altitude_attribute, time_zone='UTC'):
    """ Get list of pvlib location objects from polygon lines_

    :param polygon_layer:
    :param altitude_attribute:
    :param time_zone:
    :return:
    """

    # Get centroids and convert it to EPSG 4326 (for lat and lon)
    centroids = polygon_layer.centroid().to_crs(epsg=4326)

    # Elevation is either DEM mean computed beforehand or 0
    try:
        altitude = centroids[altitude_attribute]
        altitude = [a if not isnan(a) else 0 for a in altitude]  # Warning: no NaN in altitude !!
    except GeoLayerError:
        altitude = [0] * len(centroids)

    # Return set of locations (centroid lat and lon)
    return [Location(geom.y, geom.x, tz=time_zone, altitude=altitude[n]) for n, geom in enumerate(
        centroids.geometry)]


def hourofyear(time):
    """ Get hour of year

    :param time:
    :return:
    """
    pass
