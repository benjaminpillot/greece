# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'
from gistools.layer import GeoLayer
from gistools.raster import RasterMap
from matplotlib import pyplot as plt
import matplotlib.lines as mlines

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'

# solar_map = RasterMap("/home/benjamin/ownCloud/Post-doc Guyane/Data/Resource rasters/Monthly solar maps French "
#                       "Guyana/Irr_Total_GHI.img", no_data_value=-9999)
boundary = GeoLayer("/home/benjamin/ownCloud/Post-doc Guyane/Data/Geo layers/Cartes "
                    "administratives/admin-departement.shp")
znieff1 = GeoLayer("/home/benjamin/ownCloud/Post-doc Guyane/Data/Geo layers/znieff1/znieff1_2014_csrpn_copy1.shp")
znieff2 = GeoLayer("/home/benjamin/ownCloud/Post-doc Guyane/Data/Geo layers/znieff2/znieff2_terre_2014_s_973.shp")
places = GeoLayer("/home/benjamin/ownCloud/Post-doc Guyane/Data/Geo layers/Cartes administratives/places.shp")
routes = GeoLayer("/home/benjamin/ownCloud/Post-doc Guyane/Data/Geo layers/Cartes administratives/roads.shp")
parc_amazonien = GeoLayer("/home/benjamin/ownCloud/Post-doc Guyane/Data/Geo layers/Parc amazonien/enp_pn_s_973.shp")
reserve_naturelle_nationale = GeoLayer("/home/benjamin/ownCloud/Post-doc Guyane/Data/Geo layers/Reserve naturelle " 
                                       "nationale/n_enp_rnn_s_973.shp")
sites_inscrits = GeoLayer("/home/benjamin/ownCloud/Post-doc Guyane/Data/Geo layers/Sites "
                          "inscrits/sites_inscrits_2009.shp")
occupation_sol = GeoLayer("/home/benjamin/ownCloud/Post-doc Guyane/Data/Resource rasters/Biomasse Guyane/Occupation "
                          "sol/occupationsol_2016_annauelle_pag.shp")
series_forestieres = GeoLayer('/home/benjamin/ownCloud/Post-doc Guyane/Data/Resource rasters/Biomasse Guyane/Series '
                              'forestieres/onf_2017_series_forestieres.shp')
connection_points = GeoLayer("/home/benjamin/ownCloud/Post-doc Guyane/Data/Geo "
                             "layers/capacites-reseau/capacites-reseau.shp")

places = places[(places["type"] == "town") | (places["type"] == "village")]
ppgm = series_forestieres[series_forestieres["classement"] == "PPGM"]
sie = series_forestieres[series_forestieres["classement"] == "IE"]
production_bois = series_forestieres[series_forestieres["classement"] == "Production"]

# On passe tout en latlon EPSG=4326 (WGS84)
# places = places.to_crs(epsg=4326)
# routes = routes.to_crs(epsg=4326)
ppgm = ppgm.to_crs(epsg=4326)
sie = sie.to_crs(epsg=4326)
parc_amazonien = parc_amazonien.to_crs(epsg=4326)
znieff1 = znieff1.to_crs(epsg=4326)
znieff2 = znieff2.to_crs(epsg=4326)
reserve_naturelle_nationale = reserve_naturelle_nationale.to_crs(epsg=4326)
sites_inscrits = sites_inscrits.to_crs(epsg=4326)
occupation_sol = occupation_sol.to_crs(epsg=4326)

# Solar map
# ax = solar_map.plot(cmap="Reds", colorbar=True, colorbar_title="Yearly mean of daily irradiation (Wh/m².day)")

# Geo layers
ax = boundary.plot(layer_color="black")
# ax = places.plot(ax=ax, layer_color="black", layer_label="Cities and villages", zorder=1)
ax = parc_amazonien.plot(ax=ax, layer_color="green", layer_label="National Amazonian Park", zorder=2)
ax = reserve_naturelle_nationale.plot(ax=ax, layer_color="yellow", layer_label="National Nature Reserve", zorder=3)
ax = sites_inscrits.plot(ax=ax, layer_color="grey", layer_label="Registered sites", zorder=4)
ax = ppgm.plot(ax=ax, layer_color="cyan", layer_label="PPGM (Protection Physique et Générale des Milieux)", zorder=5)
ax = sie.plot(ax=ax, layer_color="magenta", layer_label="SIE (Série interêt écologique)", zorder=6)
ax = znieff1.plot(ax=ax, layer_color="red", layer_label="ZNIEFF type 1", zorder=7)
ax = znieff2.plot(ax=ax, layer_color="orange", layer_label="ZNIEFF type 2", zorder=8)


# ax = routes.plot(ax=ax, layer_color="black", layer_label="Road network", linewidth=0.5, zorder=7)
# ax = connection_points.plot(ax=ax, layer_color="blue", layer_label="Grid connection points", marker="*", zorder=8)

plt.axis('equal')
ax.legend(handles=ax.handles).draggable()
ax.get_legend().set_title("Légende")

plt.show()

