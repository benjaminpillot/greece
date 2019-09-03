# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'
from rentools.configuration import MainConfiguration, GridConfiguration, SolarConfiguration
from rentools.model import SolarGHIModel
from utils.sys import find_file

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


def configuration():
    return MainConfiguration(main_config_file), SolarConfiguration(solar_config_file), \
           GridConfiguration(grid_config_file)


config_dir_path = "/home/benjamin/Documents/Post-doc Guyane/Data/Config files"

# Create configuration
try:
    main_config_file = find_file("main.config", config_dir_path)[0]
    grid_config_file = find_file("grid.config", config_dir_path)[0]
    solar_config_file = find_file("solar.config", config_dir_path)[0]
except (IndexError, ValueError):
    raise RuntimeError("Unable to locate configuration file(s): check that main.config, grid.config and "
                       "solar.config are correctly located in directory '%s'" % config_dir_path)

main_config, solar_config, grid_config = configuration()
solar_resource_model = SolarGHIModel(main_config, solar_config, grid_config)
solar_resource_model.extract_polygons()
