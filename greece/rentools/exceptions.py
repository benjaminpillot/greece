# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# import

# __all__ = []
# __version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


class ModelError(Exception):
    pass


class GeoModelError(ModelError):
    pass


class SpatialExtractionModelError(Exception):
    pass


class SpatialRasterResourceModelError(Exception):
    pass


class PolygonMapError(GeoModelError):
    pass


class RasterResourceMapError(PolygonMapError):
    pass


class ConfigurationError(Exception):
    pass


class ConstraintConfigurationError(ConfigurationError):
    pass


class ResourceConfigurationError(ConstraintConfigurationError):
    pass


class MainConfigurationError(ConfigurationError):
    pass


class NetworkConfigurationError(ConfigurationError):
    pass


class ConfigurationParserError(Exception):
    pass


class NetworkConfigurationParserError(ConfigurationParserError):
    pass


class GridConfigurationParserError(NetworkConfigurationParserError):
    pass


class MainConfigurationParserError(ConfigurationParserError):
    pass


class ResourceConfigurationParserError(ConfigurationParserError):
    pass


class NetworkModelError(Exception):
    pass


class MixedGenerationConfigurationError(ConfigurationError):
    pass


class MixedEnergyModelError(ModelError):
    pass


class PVSystemConfigurationParserError(ConfigurationParserError):
    pass


class PVSystemConfigurationError(ConfigurationError):
    pass


class PVSystemConfigurationWarning(Warning):
    pass


if __name__ == "__main__":
    pass
