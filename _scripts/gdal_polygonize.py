# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# import

# __all__ = []
# __version__ = '0.1'
import rasterio
import time

from matplotlib import pyplot
from osgeo import gdal, ogr, osr
import numpy as np
from rasterio.features import sieve, shapes

from gistools.conversion import array_to_raster, raster_to_array
from gistools.coordinates import GeoGrid
from gistools.layer import GeoLayer
from gistools.projections import ellipsoid_from, proj4_from_raster

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


gdal.UseExceptions()
ogr.UseExceptions()

slope = "/home/benjamin/ownCloud/Post-doc Guyane/Data/DEM/guyana_slope_90m"

# boundary = "/home/benjamin/ownCloud/Post-doc Guyane/Data/Geo layers/Cartes administratives/admin-departement.shp"
# lines_ = GeoLayer(boundary)
# lines_["burn_value"] = 1
# geo_grid = GeoGrid.from_geo_file(boundary, 0.05, 0.1)
# array = lines_.to_array(geo_grid, 'burn_value')
# array_to_raster('test_raster.tif', array, geo_grid, lines_.crs)


slope_array = raster_to_array(slope)
geo_grid = GeoGrid.from_raster_file(slope)
test = np.zeros(slope_array.shape)
# Classification
test[(slope_array <= 5) & (slope_array >= 0)] = 1
# test[(slope_array > 5) & (slope_array <= 10)] = 2
crs = proj4_from_raster(slope)
array_to_raster('test_raster.tif', test, geo_grid, crs)

# Test with gdal sieve filter
# sieved = np.zeros(test.shape)
# array_to_raster('test_raster_sieved.tif', sieved, geo_grid, crs)

src_ds = gdal.Open('test_raster.tif')
src_band = src_ds.GetRasterBand(1)
drv = gdal.GetDriverByName('GTiff')
dst_ds = drv.Create('test_raster_sieved.tif', test.shape[1], test.shape[0], 1, gdal.GDT_Byte)
dst_band = dst_ds.GetRasterBand(1)
gdal.SieveFilter(src_band, None, dst_band, 20, 4)

# dst_band = None
# dst_ds = None

del dst_band, dst_ds

# Get array from raster
sieved = raster_to_array('test_raster_sieved.tif')

pyplot.imshow(sieved)
pyplot.show()

# with rasterio.drivers():
#
#     with rasterio.open('test_raster.tif') as src:
#         shade = src.read(1)
#
#     print("Slope shapes: %d" % len(list(test_shape)))
    #
    # sieved = sieve(shade, 50)
#
# array_to_raster('test_raster_sieved.tif', sieved, geo_grid, crs)

# print("Slope shapes: %d" % len(list(shapes(sieved))))

# pyplot.figure(1)
# pyplot.imshow(test)
# pyplot.figure(2)
# pyplot.imshow(sieved)
# pyplot.show()

# print("Sieved shapes: %d" % len(list(shapes(sieved))))


# src_ds = gdal.Open("test_raster_sieved.tif")
# srcband = src_ds.GetRasterBand(1)
# drv = ogr.GetDriverByName("ESRI Shapefile")
# dst_ds = drv.CreateDataSource("test_polygonized.shp")
# srs = osr.SpatialReference()
# srs.ImportFromWkt(src_ds.GetProjectionRef())
# dst_layer = dst_ds.CreateLayer("test_polygonized", srs)
#
# fd = ogr.FieldDefn('slope', ogr.OFTInteger)
# dst_layer.CreateField(fd)
#
# gdal.Polygonize(srcband, srcband.GetMaskBand(), dst_layer, 0)
#
# dst_ds.Destroy()

# _new_layer = GeoLayer("test_polygonized.shp")
# _new_layer.plot()
# pyplot.show()


if __name__ == "__main__":
    pass
