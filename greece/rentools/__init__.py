# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'
import os

import pvlib

from greece import data_dir

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


_sam_database = os.path.join(data_dir, "sam_database")
_path_to_config = os.path.join(data_dir, ".config")


# Constants
VALID_RASTER_FORMATS = dict(tiff=".tif", img=".img")
VALID_LAYER_DRIVERS = {".shp": "ESRI Shapefile", ".geojson": "GeoJSON"}
VALID_FILE_FORMATS = dict(table=".csv")
SANDIA_MODULE_DATABASE = pvlib.pvsystem.retrieve_sam(path=os.path.join(_sam_database, "sandia_modules.csv"))
CEC_MODULE_DATABASE = pvlib.pvsystem.retrieve_sam(path=os.path.join(_sam_database, "cec_modules.csv"))
CEC_INVERTER_DATABASE = pvlib.pvsystem.retrieve_sam(path=os.path.join(_sam_database, "cec_inverters.csv"))
SANDIA_MODULE_NAMES = list(SANDIA_MODULE_DATABASE.columns)
CEC_MODULE_NAMES = list(CEC_MODULE_DATABASE.columns)
VALID_MODULE_NAMES = SANDIA_MODULE_NAMES + CEC_MODULE_NAMES
VALID_INVERTER_NAMES = list(CEC_INVERTER_DATABASE.columns)
