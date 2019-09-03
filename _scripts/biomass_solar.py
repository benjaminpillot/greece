# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


from gistools.layer import PolygonLayer


biomass = PolygonLayer("/home/benjamin/ownCloud/Post-doc Guyane/GREECE model/Results/Biomass/generation.geojson")
solar_pv = PolygonLayer("/home/benjamin/ownCloud/Post-doc Guyane/GREECE model/Results/Solar PV/result.geojson")

solar_pv["Polygon"] = ["PV %d" % n for n in range(len(solar_pv))]
solar_pv["Nature"] = ["PV"] * len(solar_pv)

area = biomass.attr_area(solar_pv, "Nature", normalized=True)
polygon = biomass.attr_area(solar_pv, "Polygon", normalized=True)

# print(area)
# print(len(biomass))
print(area['PV'])
print(polygon['PV 0'])
