# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

from gistools.layer import GeoLayer, PolygonLayer

# __all__ = []
# __version__ = '0.1'
from utils.sys.timer import Timer

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


poly = "/home/benjamin/Documents/Post-doc Guyane/Data/Base lines_/flat_slope_layer.shp"
parc = "/home/benjamin/ownCloud/Post-doc Guyane/Data/Geo layers/Parc amazonien/enp_pn_s_973.shp"

slope_layer = PolygonLayer(poly)
with Timer() as t:
    slope_layer = slope_layer.explode()
print("explode time: %s" % t)

slope_layer.to_file("/home/benjamin/Documents/Post-doc Guyane/Data/Base lines_/flat_slope_layer_explode_test.shp")

# amazonian_parc = GeoLayer(parc)
# amazonian_parc = amazonian_parc.explode()

# test = slope_layer.overlay(amazonian_parc, how="difference")
