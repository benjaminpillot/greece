# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# import

# __all__ = []
# __version__ = '0.1'
import numpy as np
from gistools.layer import GeoLayer
from gistools.raster import RasterMap
from rentools.resource import get_resource_within_layer_of_polygons, RasterResourceMap

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


resource_polygons = GeoLayer("/home/benjamin/ownCloud/Post-doc Guyane/PycharmProjects/GuyanaDataTool/rentools/"
                             "resource_polygons_2.shp")
solar_map = RasterMap("/home/benjamin/ownCloud/Post-doc Guyane/Data/Resource rasters/Monthly solar maps French "
                      "Guyana/Irr_Total_GHI_resampled.tif", no_data_value=-9999)

resource = get_resource_within_layer_of_polygons(resource_polygons, solar_map)

resource_polygons["area"] = resource_polygons.area
# polygons["polygon id"] = np.arange(0, len(polygons))

test = RasterResourceMap(solar_map, resource_polygons, )

array = resource_polygons.to

if __name__ == "__main__":
    pass
