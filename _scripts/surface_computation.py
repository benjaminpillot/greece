# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'
from gistools.projections import proj4_from_raster, ellipsoid_from

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'

import geopandas as gpd
import numpy as np
from gistools.coordinates import GeoGrid, Ellipsoid
from gistools.conversion import geopandas_to_array, raster_to_array
from gistools.surface import compute_surface

# Other test with UTM...
slope = "/home/benjamin/Documents/PENTE_MNE_SRTM_30m.tif"
slope_array = raster_to_array(slope)
geo_grid = GeoGrid.from_raster_file(slope)
test = np.zeros(slope_array.shape)
test[slope_array >= 0] = 1
crs = proj4_from_raster(slope)
surface = compute_surface(geo_grid.longitude_mesh - geo_grid.res/2, geo_grid.longitude_mesh + geo_grid.res/2,
                          geo_grid.latitude_mesh + geo_grid.res/2, geo_grid.latitude_mesh - geo_grid.res/2, "equal",
                          ellipsoid_from(crs))
surface = surface * test
surface_total = surface.sum()

geo_file = '/home/benjamin/ownCloud/Post-doc Guyane/Data/Cartes administratives/admin-departement.shp'
test = gpd.read_file(geo_file)
test = test.to_crs({'proj': 'cea'})
test["burn_value"] = 1

geo_grid = GeoGrid.adapt_to_geopandas(test, 1000)
array_test = geopandas_to_array(test, "burn_value", geo_grid)

surface = compute_surface(geo_grid.longitude_mesh - geo_grid.res/2, geo_grid.longitude_mesh + geo_grid.res/2,
                          geo_grid.latitude_mesh + geo_grid.res/2, geo_grid.latitude_mesh - geo_grid.res/2, "equal",
                          Ellipsoid("wgs84"))
surface = surface * array_test
surface_total = surface.sum()
gpd_area = test.geometry.area[0]

print("Surface computed after cea reprojection: {} m^2".format(surface_total))
print("Surface computed by geopandas: {} m^2".format(gpd_area))
