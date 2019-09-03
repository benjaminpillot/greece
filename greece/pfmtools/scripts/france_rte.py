# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""
import pandas as pd
from matplotlib import pyplot as plt
from gistools import PolygonLayer
from utils.sys.timer import Timer

from greece.pfmtools.grid import PowerLine, Substation

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2019, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'

# overhead_lines = PowerLine("/home/benjamin/Desktop/Power Grid/RTE/lignes-aeriennes-rte.geojson")
# underground_lines = PowerLine("/home/benjamin/Desktop/Power Grid/RTE/lignes-souterraines-rte.geojson")
# with Timer() as t:
#     overhead_lines = overhead_lines.clean_topology()
#     underground_lines = underground_lines.clean_topology()
# print("spent time: %s" % t)
#
# overhead_lines.to_file("/home/benjamin/Desktop/Power Grid/RTE/power data/france_overhead_pwlines.geojson",
#                        driver="GeoJSON")
# underground_lines.to_file("/home/benjamin/Desktop/Power Grid/RTE/power data/france_underground_pwlines.geojson",
#                           driver="GeoJSON")

# overhead_lines = PowerLine("/home/benjamin/Desktop/Power Grid/RTE/power data/france_overhead_pwlines.geojson")
# underground_lines = PowerLine("/home/benjamin/Desktop/Power Grid/RTE/power data/france_underground_pwlines.geojson")
#
# with Timer() as t:
#     france_pwlines = overhead_lines.append(underground_lines).clean_topology()  # t = 200 s.
# print("time: %s" % t)
#
# france_pwlines.to_file("/home/benjamin/Desktop/Power Grid/RTE/power data/france_pwlines.geojson")

# dataframe = pd.read_csv("/home/benjamin/Desktop/Power Grid/RTE/registre-national-installation-production-"
#                         "stockage-electricite-agrege.csv")
# df = dataframe[~dataframe["CODE_IRIS"].isna()]
# iris = PolygonLayer("/home/benjamin/Desktop/CONTOURS_IRIS_2015/1_DONNEES_LIVRAISON_2015/"
#                     "CONTOURS-IRIS_2-1_SHP_LAMB93_FE-2015/CONTOURS-IRIS.shp").clean_geometry()
# power_stations = pandas_to_layer(df, iris, "CODE_IRIS")
# power_stations.to_file("/home/benjamin/Desktop/Power Grid/RTE/power data/france_pwstations.geojson", driver="GeoJSON")

france_pwlines = PowerLine("/home/benjamin/Desktop/Power Grid/RTE/power data/france_pwlines/france_pwlines.shp",
                           "tension")
france_substations = Substation("/home/benjamin/Desktop/Power Grid/RTE/power data/enceintes-poste-rte.geojson",
                                "tensionmax")
ending_nodes, _ = france_pwlines.get_end_nodes()

ending_nodes = ending_nodes.overlay(france_substations, how="difference")

france_pwlines.plot(layer_color="blue")
ending_nodes.plot(layer_color="red")
plt.show()
