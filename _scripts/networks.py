# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'
from utils.sys.timer import Timer
from gistools.raster import DigitalElevationModel
from gistools.network import Road
from gistools.layer import PolygonLayer
from matplotlib import pyplot

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'

from gistools.network import Road
road = Road("/home/benjamin/Documents/Post-doc Guyane/Data/Geo layers/RESEAU_ROUTIER/TRONCON_ROUTE.SHP")
# biomass = PolygonLayer("/home/benjamin/Documents/Post-doc Guyane/Data/Results/Biomass/polygons.geojson")

# biomass_point = biomass.project(road)
# nearest_segment_points = road.nearest_point_in_layer(biomass_point)

# t_time = road.travel_time('ETAT', {'Non revêtu': 70, 'Revêtu': 90, 'Sentier': 50, "Chemin d'exploitation": 40},
#                           'ETAT', {'Non revêtu': 0.015, 'Revêtu': 0.01, 'Sentier': 0.02,
#                                    "Chemin d'exploitation": 0.02}, acceleration_rate=1.5, gross_hp=500,
#                           vehicle_weight=30000, speed_format='km/h')

# t_time_test = []

# for n, t in enumerate(t_time["one-way"]):
#     break_idx = [loc[1] for loc in nearest_segment_points if loc[0] == n]
#     if len(break_idx) == 0:
#         t_time_test.append(t)
#     else:
#         t_time_test.extend(split_list_by_index(t, break_idx, include=False))


# test = PolygonLayer("/home/benjamin/Documents/Post-doc Guyane/Data/Results/Solar/polygons.shp")
# road = Road("/home/benjamin/Documents/Post-doc Guyane/Data/Geo layers/Road network/main_road_network.shp")
# road = Road("/home/benjamin/Documents/Post-doc Guyane/Data/Geo layers/RESEAU_ROUTIER/TRONCON_ROUTE.SHP")
# road = road.to_crs(test.crs)
# point = test.project(road)
# with Timer() as t:
#     new_road = road.split_at_points(point)
# print("%.3f s" % t.elapsed)
# new_road.build_graph()
# nodes = new_road.get_nodes()
# road.plot(layer_color="blue")
# nodes.plot(layer_color="red")
# pyplot.show()

with Timer() as t:
    while "There is still disconnected islands":
        new_road = road.find_disconnected_islands_and_fix()
        if len(new_road) < len(road):
            road = new_road
        else:
            break
print(t)
#
with Timer() as t:
    new_road = new_road.add_points_to_geometry(30)
print(t)
new_road = new_road.to_crs({'init': 'epsg:32622'})
dem = DigitalElevationModel("/home/benjamin/Documents/Post-doc Guyane/Data/DEM/srtm_guyana_1_arc_second.tif")
dem = dem.to_crs({'init': 'epsg:32622'})
new_road = new_road.add_z(dem)
schema = new_road.schema
schema['geometry'] = '3D LineString'
#
new_road.to_file("/home/benjamin/Documents/Post-doc Guyane/Data/Geo layers/Road network/main_road_network.shp",
                 schema=schema)
