# -*- coding: utf-8 -*-

""" ConfigurationParser file reading module

Methods for reading configuration files
related to resource module
"""

import inspect
import os
import pytz

from abc import ABCMeta, abstractmethod
from gistools.projections import proj4_from
from utils.check import isfile
from utils.check.value import check_value_in_range

from greece.rentools import VALID_RASTER_FORMATS, VALID_LAYER_DRIVERS, VALID_FILE_FORMATS, VALID_MODULE_NAMES, \
    VALID_INVERTER_NAMES
from greece.rentools.exceptions import ConfigurationParserError, MainConfigurationParserError, \
    ResourceConfigurationParserError, PVSystemConfigurationParserError

__version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


class ConfigurationParser(metaclass=ABCMeta):
    """ Parse configuration from config file

    """

    _read_main_config_attributes = dict()

    def __init__(self, config_file):
        """ Initiate configuration class

        :param config_file: path to configuration file
        :return:
        """
        self.config_file = config_file

        if not self.is_valid_config_file():
            raise ConfigurationParserError("Invalid configuration file '%s'" % config_file)

    def parse(self):
        """ Read configuration file

        Read configuration attributes from configuration file
        :return:
        """
        with open(self.config_file) as config_file:
            # Use strip() string method to delete leading and ending spaces
            temp = [line.strip() for line in config_file.read().splitlines() if line != '']

        # Read config file
        for line in temp:
            if not line.startswith("#"):
                key, value = [field.strip() for field in line.split(sep="=")]
                if key in self._read_main_config_attributes.keys():
                    self._read_main_config_attributes[key](key, value)

        return self

    #########################
    # Abstract, class methods

    @abstractmethod
    def is_valid_config_file(self):
        pass

    @classmethod
    def get_attributes(cls):
        attributes = []
        base_cls = [c for c in inspect.getmro(cls) if c is not object]
        for base in base_cls[::-1]:
            attributes.extend([a for a in base.__dict__.keys() if not a.startswith('_')
                               and not callable(getattr(cls, a))])

        return attributes

    @classmethod
    def build_default_config_file(cls, name, directory=os.getcwd()):
        """ Build default config file

        :param name:
        :param directory:
        :return:
        """
        attributes = cls.get_attributes()
        path_to_file = os.path.join(directory, "%s.config" % name)
        with open(path_to_file, "w+") as file:
            file.write("# Default %s.config file for GREECE model\n\n# All text after a hash (#) is regarded as a "
                       "comment and will be ignored\n\n" % name)
            for attr in attributes:
                file.write("%s=\n\n" % attr)

        return 0

    @classmethod
    def str_to_num(cls, string, num_class):
        if string == '':
            return None
        else:
            return num_class(string)

    ###################
    # Protected methods
    def _set_among_valid_values(self, attr, value, valid_values):
        self._set_configuration_attribute(attr, value)
        if value:  # Empty string are False in Python
            if value not in valid_values:
                raise ConfigurationParserError("Field '%s' cannot be set: value must be in '%s'" % (attr, valid_values))

    def _set_boolean(self, attr, boolean):
        self._set_among_valid_values(attr, boolean.lower(), ["true", "false"])

    def _set_configuration_attribute(self, attr, value):
        d = {'': None, 'true': True, 'false': False}
        if value in d.keys():
            value = d[value]
        if value is not None:
            try:
                self.__setattr__(attr, value)
            except AttributeError:
                raise ConfigurationParserError("Not a valid field '%s'" % attr)

    def _set_destination_path(self, attr, path, valid_format):
        self._set_configuration_attribute(attr, path)
        if path:
            if not os.path.isdir(os.path.split(path)[0]):
                raise ConfigurationParserError("Field '%s' cannot be set: '%s' is not a valid path" % (attr, path))
            if os.path.splitext(path)[1] not in valid_format:
                raise ConfigurationParserError("Field '%s' cannot be set: invalid file extension" % attr)

    def _set_table_destination_path(self, attr, path):
        self._set_destination_path(attr, path, VALID_FILE_FORMATS["table"])

    def _set_layer_destination_path(self, attr, path):
        self._set_destination_path(attr, path, VALID_LAYER_DRIVERS.keys())

    def _set_integer(self, attr, value):
        try:
            self._set_configuration_attribute(attr, self.str_to_num(value, int))
        except ValueError:
            raise ConfigurationParserError("Field '%s' cannot be set: '%s' is not an integer" % (attr, value))

    def _set_float(self, attr, value):
        try:
            self._set_configuration_attribute(attr, self.str_to_num(value, float))
        except ValueError:
            raise ConfigurationParserError("Field '%s' cannot be set: '%s' is not a valid numeric value" % (attr,
                                                                                                            value))

    def _set_float_in_range(self, attr, value, v_min, v_max):
        self._set_float(attr, value)
        if value:
            try:
                check_value_in_range(self.__getattribute__(attr), v_min, v_max)
            except ValueError:
                raise ConfigurationParserError("Field '%s' cannot be set: value '%s' must be in [%.2g %.2g]" %
                                               (attr, value, v_min, v_max))

    def _set_positive_float(self, attr, value):
        self._set_float(attr, value)
        if value:
            if self.__getattribute__(attr) <= 0:
                raise ConfigurationParserError("Field '%s' cannot be set: must be positive but is '%s'" % (attr, value))

    def _set_positive_integer(self, attr, value):
        self._set_positive_float(attr, value)
        self._set_integer(attr, value)

    def _set_path_to_file(self, attr, path):
        self._set_configuration_attribute(attr, path)
        if path:
            if not isfile(path):
                raise ConfigurationParserError("Field '%s' cannot be set: '%s' is not a valid file" % (attr, path))

    def _set_path_to_layer_file(self, attr, path):
        self._set_path_to_file(attr, path)
        if path:
            if os.path.splitext(path)[1] not in VALID_LAYER_DRIVERS.keys():
                raise ConfigurationParserError("'%s' is not a valid lines_ file" % attr)

    def _set_path_to_directory(self, attr, path):
        self._set_configuration_attribute(attr, path)
        if path:
            if not os.path.isdir(path):
                raise ConfigurationParserError("Field '%s' cannot be set: '%s' is not a valid directory" % (attr, path))

    def _set_time_zone(self, attr, tz):
        self._set_among_valid_values(attr, tz, pytz.all_timezones)


class MainConfigurationParser(ConfigurationParser):
    """ Define main configuration

    """
    CRS = None
    SURFACE_CRS = None
    PATH_TO_DEM_FILE = None
    PATH_TO_LAND_USE_FILE = None
    LAND_USE_ATTRIBUTE = None

    def __init__(self, config_file):
        super().__init__(config_file)

        self._read_main_config_attributes.update(CRS=self._set_crs, SURFACE_CRS=self._set_crs,
                                                 PATH_TO_DEM_FILE=self._set_path_to_file,
                                                 PATH_TO_LAND_USE_FILE=self._set_path_to_file,
                                                 LAND_USE_ATTRIBUTE=self._set_configuration_attribute)

    def is_valid_config_file(self):
        return True

    ###################
    # Protected methods
    def _set_crs(self, attr, crs):
        try:
            self._set_configuration_attribute(attr, proj4_from({'init': crs}))
        except ValueError:
            try:
                self._set_configuration_attribute(attr, proj4_from({'proj': crs}))
            except ValueError:
                raise MainConfigurationParserError("'%s' cannot be set: invalid CRS '%s'" % (attr, crs))


class TransportationConfigurationParser(ConfigurationParser):
    """ Define transportation configuration

    Class used for implementing vehicle
    and transportation parameters from
    a configuration file
    """

    USE_CENTROID_PROJECTION = False

    def __init__(self, config_file):
        super().__init__(config_file)

        self._read_main_config_attributes.update(USE_CENTROID_PROJECTION=self._set_boolean)

    def is_valid_config_file(self):
        return True


class RoadTransportationConfigurationParser(TransportationConfigurationParser):
    """ Define road transportation configuration

    """

    TIME_FORMAT = None
    TARE_WEIGHT = None
    GROSS_WEIGHT = None
    GROSS_HORSE_POWER = None
    FRONTAL_AREA = None
    ENGINE_EFFICIENCY = None
    FUEL_VOLUMETRIC_ENERGY_DENSITY = None
    UPHILL_HORSE_POWER_RATE = 0.8
    DOWNHILL_HORSE_POWER_RATE = 0.6
    DRAG_RESISTANCE = 0.35
    MASS_CORRECTION_FACTOR = 1.05
    ACCELERATION_RATE = 0.5
    DECELERATION_RATE = 3

    def __init__(self, config_file):
        super().__init__(config_file)

        self._read_main_config_attributes.update(
            TIME_FORMAT=self._set_time_format, TARE_WEIGHT=self._set_positive_float,
            GROSS_WEIGHT=self._set_positive_float, GROSS_HORSE_POWER=self._set_positive_float,
            FRONTAL_AREA=self._set_positive_float, ENGINE_EFFICIENCY=self._set_efficiency,
            FUEL_VOLUMETRIC_ENERGY_DENSITY=self._set_positive_float, UPHILL_HORSE_POWER_RATE=self._set_efficiency,
            DOWNHILL_HORSE_POWER_RATE=self._set_efficiency, DRAG_RESISTANCE=self._set_positive_float,
            MASS_CORRECTION_FACTOR=self._set_positive_float, ACCELERATION_RATE=self._set_positive_float,
            DECELERATION_RATE=self._set_positive_float)

    def _set_efficiency(self, attr, value):
        self._set_float_in_range(attr, value, 0, 1)

    def _set_time_format(self, attr, value):
        self._set_among_valid_values(attr, value.lower(), {'s', 'm', 'h'})


class NetworkConfigurationParser(ConfigurationParser):
    """ Define network configuration

    Class used for implementation of
    network-based model parameters from
    a configuration file
    """

    # ConfigurationParser fields
    PATH_TO_EDGE_FILE = None
    PATH_TO_NODE_FILE = None
    FIND_DISCONNECTED_ISLANDS_AND_FIX = False
    FIND_AND_FIX_METHOD = None
    FIND_AND_FIX_TOLERANCE = None
    MATCH_EDGE_NODES = None
    ADD_Z_DIMENSION = False
    NODE_TOLERANCE = None
    EDGE_RESOLUTION = None
    PATH_TO_DIRECTION_CONFIG_FILE = None

    def __init__(self, config_file):
        super().__init__(config_file)

        self._read_main_config_attributes.update(
            PATH_TO_EDGE_FILE=self._set_path_to_file, PATH_TO_NODE_FILE=self._set_path_to_file,
            FIND_DICONNECTED_ISLANDS_AND_FIX=self._set_boolean, FIND_AND_FIX_METHOD=self._set_find_and_fix_method,
            FIND_AND_FIX_TOLERANCE=self._set_positive_float, MATCH_EDGE_NODES=self._set_boolean,
            ADD_Z_DIMENSION=self._set_boolean, NODE_TOLERANCE=self._set_positive_float,
            EDGE_RESOLUTION=self._set_positive_float, PATH_TO_DIRECTION_CONFIG_FILE=self._set_path_to_file)

    def is_valid_config_file(self):
        return True

    ###################
    # Protected methods

    def _set_find_and_fix_method(self, attr, value):
        self._set_among_valid_values(attr, value.lower(), {'reconnect_and_delete', 'reconnect_and_keep', 'delete'})


class GridConfigurationParser(NetworkConfigurationParser):
    """ Define electrical grid configuration

    """

    MODEL = None

    def __init__(self, config_file):
        super().__init__(config_file)

        self._read_main_config_attributes.update(MODEL=self._set_model)

    ###################
    # Protected methods
    def _set_model(self, attr, model):
        self._set_among_valid_values(attr, model.lower(), {'minimum_distance', 'power_flow'})


class RoadNetworkConfigurationParser(NetworkConfigurationParser):
    """ Define road network configuration

    """
    # ConfigurationParser fields
    PATH_TO_ROLLING_COEFFICIENT_CONFIG_FILE = None
    PATH_TO_ROLLOVER_CRITERION_CONFIG_FILE = None
    PATH_TO_SPEED_LIMIT_CONFIG_FILE = None
    PATH_TO_NODE_SPEED_CONFIG_FILE = None
    SPEED_FORMAT = "km/h"

    def __init__(self, config_file):
        super().__init__(config_file)

        self._read_main_config_attributes.update(PATH_TO_ROLLING_COEFFICIENT_CONFIG_FILE=self._set_path_to_file,
                                                 PATH_TO_ROLLOVER_CRITERION_CONFIG_FILE=self._set_path_to_file,
                                                 PATH_TO_SPEED_LIMIT_CONFIG_FILE=self._set_path_to_file,
                                                 PATH_TO_NODE_SPEED_CONFIG_FILE=self._set_path_to_file,
                                                 SPEED_FORMAT=self._set_speed_format)

    def _set_speed_format(self, attr, s_format):
        self._set_among_valid_values(attr, s_format.lower(), {'m/s', 'km/h'})


class ConstraintConfigurationParser(ConfigurationParser):
    """

    """
    # ConfigurationParser fields
    BASE_LAYER_METHOD = None
    PATH_TO_BASE_LAYER_FILE = None
    SLOPE_THRESHOLD = None
    SIEVE_FILTER_MINIMUM_CONNECTION = None
    IS_8_CONNECTED = False
    SIMPLIFY_TOLERANCE = None
    PATH_TO_DISTANCE_THRESHOLD_DIRECTORY = None
    PATH_TO_DISTANCE_THRESHOLD_CONFIG_FILE = None
    PATH_TO_DISTANCE_FROM_POLYGON_TO_LAYER_DIRECTORY = None
    PATH_TO_DISTANCE_FROM_POLYGON_TO_LAYER_CONFIG_FILE = None
    PATH_TO_MASK_DIRECTORY = None
    PATH_TO_MASK_CONFIG_FILE = None
    COMPUTE_DISTANCE_FROM_CENTROID = False
    FAST_INTERSECTION_SURFACE_THRESHOLD = 2000000
    MIN_POLYGON_SURFACE = 0
    MAX_POLYGON_SURFACE = None
    SPLIT_METHOD = "partition"
    SPLIT_SHAPE = "hexagon"
    DISAGGREGATION_FACTOR = 16
    METRIC_PRECISION = 100
    METIS_NCUTS = 10
    METIS_OBJTYPE = "cut"
    METIS_IPTYPE = "edge"
    METIS_RTYPE = "greedy"
    COMPUTE_SHAPE_FACTOR = False
    USE_CONVEX_HULL_SHAPE = True
    COMPUTE_DEM_STATISTICS = False
    EXTRACT_LAND_USE = False
    SAVE_POLYGON_LAYER_TO = None
    SAVE_POLYGON_TABLE_TO = None

    def __init__(self, config_file):

        super().__init__(config_file)

        self._read_main_config_attributes.update(
            BASE_LAYER_METHOD=self._set_base_layer_method, SLOPE_THRESHOLD=self._set_slope_threshold,
            SIEVE_FILTER_MINIMUM_CONNECTION=self._set_positive_integer, IS_8_CONNECTED=self._set_boolean,
            PATH_TO_BASE_LAYER_FILE=self._set_path_to_file, SIMPLIFY_TOLERANCE=self._set_positive_float,
            PATH_TO_DISTANCE_THRESHOLD_DIRECTORY=self._set_path_to_directory,
            PATH_TO_DISTANCE_THRESHOLD_CONFIG_FILE=self._set_path_to_file,
            PATH_TO_MASK_DIRECTORY=self._set_path_to_directory, PATH_TO_MASK_CONFIG_FILE=self._set_path_to_file,
            PATH_TO_DISTANCE_FROM_POLYGON_TO_LAYER_DIRECTORY=self._set_path_to_directory,
            PATH_TO_DISTANCE_FROM_POLYGON_TO_LAYER_CONFIG_FILE=self._set_path_to_file,
            COMPUTE_DISTANCE_FROM_CENTROID=self._set_boolean,
            FAST_INTERSECTION_SURFACE_THRESHOLD=self._set_positive_float, MIN_POLYGON_SURFACE=self._set_positive_float,
            MAX_POLYGON_SURFACE=self._set_positive_float, SPLIT_METHOD=self._set_split_method,
            SPLIT_SHAPE=self._set_split_shape, DISAGGREGATION_FACTOR=self._set_positive_integer,
            METRIC_PRECISION=self._set_positive_integer, METIS_NCUTS=self._set_positive_integer,
            METIS_OBJTYPE=self._set_objtype, METIS_IPTYPE=self._set_iptype, METIS_RTYPE=self._set_rtype,
            COMPUTE_SHAPE_FACTOR=self._set_boolean, USE_CONVEX_HULL_SHAPE=self._set_boolean,
            COMPUTE_DEM_STATISTICS=self._set_boolean, EXTRACT_LAND_USE=self._set_boolean,
            SAVE_POLYGON_LAYER_TO=self._set_layer_destination_path,
            SAVE_POLYGON_TABLE_TO=self._set_table_destination_path)

    def is_valid_config_file(self):
        # TODO: check validity of configuration file
        return True

    ###################
    # Protected methods

    def _set_base_layer_method(self, attr, method):
        self._set_among_valid_values(attr, method.lower(), {'slope', 'file'})

    def _set_iptype(self, attr, iptype):
        self._set_among_valid_values(attr, iptype.lower(), {'grow', 'random', 'edge', 'node'})

    def _set_objtype(self, attr, objtype):
        self._set_among_valid_values(attr, objtype.lower(), {'cut', 'vol'})

    # def _set_partition_weight(self, attr, w):
    #     self._set_among_valid_values(attr, w.lower(), {"area", "length"})

    def _set_rtype(self, attr, rtype):
        self._set_among_valid_values(attr, rtype.lower(), {'fm', 'greedy', 'sep2sided', 'sep1sided'})

    def _set_split_method(self, attr, method):
        self._set_among_valid_values(attr, method.lower(), {'partition', 'simple'})

    def _set_split_shape(self, attr, shape):
        self._set_among_valid_values(attr, shape.lower(), {'square', 'hexagon'})

    def _set_slope_threshold(self, attr, threshold):
        self._set_float_in_range(attr, threshold, 0, 100)


class ResourceConfigurationParser(ConstraintConfigurationParser):

    PATH_TO_RESOURCE = None
    IDENTIFY_RESOURCE_CONTOUR_ZONES = False
    CONTOUR_INTERVAL_TYPE = "absolute"
    CONTOUR_INTERVAL_VALUE = None
    MAIN_PERCENTILE_RANGE = None
    USE_RESOURCE_GENERATOR = False
    RESOURCE_GENERATOR = None
    SAVE_RESOURCE_TABLE_TO = None

    def __init__(self, config_file):

        super().__init__(config_file)

        self._read_main_config_attributes.update(
            PATH_TO_RESOURCE=self._set_path_to_resource, IDENTIFY_RESOURCE_CONTOUR_ZONES=self._set_boolean,
            CONTOUR_INTERVAL_TYPE=self._set_contour_interval_type, CONTOUR_INTERVAL_VALUE=self._set_contour_interval,
            MAIN_PERCENTILE_RANGE=self._set_percentile_range, SAVE_RESOURCE_TABLE_TO=self._set_table_destination_path,
            USE_RESOURCE_GENERATOR=self._set_boolean, RESOURCE_GENERATOR=self._set_resource_generator)

    def _set_contour_interval(self, attr, value):
        self._set_positive_float(attr, value)
        if self.CONTOUR_INTERVAL_TYPE == 'relative':
            self._set_float_in_range(attr, value, 0, 100)

    def _set_contour_interval_type(self, attr, value):
        self._set_among_valid_values(attr, value, {'absolute', 'relative'})

    def _set_percentile_range(self, attr, value):
        self._set_float_in_range(attr, value, 0, 100)

    def _set_path_to_resource(self, attr, path):
        try:
            self._set_path_to_file(attr, path)
        except ConfigurationParserError:
            try:
                self._set_path_to_directory(attr, path)
            except ConfigurationParserError:
                raise ResourceConfigurationParserError("Field '%s' cannot be set: invalid path '%s'" % (attr, path))

    def _set_resource_generator(self, attr, generator):
        self._set_among_valid_values(attr, generator.lower(), {'daily', 'hourly', 'daily_and_hourly'})

    def is_valid_config_file(self):
        # TODO: check validity of configuration file
        return True


class RasterResourceConfigurationParser(ResourceConfigurationParser):
    """ Define configuration from config file

    Class used in combination with RasterResourceMap
    class for implementation of model parameters from a
    configuration file
    """
    # ConfigurationParser fields
    RASTER_FORMAT = None
    NO_DATA_VALUE = None
    RESAMPLING_FACTOR = None
    ALL_TOUCHED = False
    SURFACE_WEIGHTED = False

    def __init__(self, config_file):

        super().__init__(config_file)

        self._read_main_config_attributes.update(
            NO_DATA_VALUE=self._set_float, RASTER_FORMAT=self._set_raster_format,
            RESAMPLING_FACTOR=self._set_positive_integer, ALL_TOUCHED=self._set_boolean,
            SURFACE_WEIGHTED=self._set_boolean)

    def is_valid_config_file(self):
        # TODO: check validity of configuration file
        return True

    ###################
    # Protected methods

    def _set_raster_format(self, attr, r_format):
        self._set_among_valid_values(attr, r_format.lower(), VALID_RASTER_FORMATS.keys())


class ResourceToGenerationConfigurationParser(ConfigurationParser):

    # Fields
    PATH_TO_GENERATION_CONFIG_FILE = None
    PATH_TO_RESOURCE_CONFIG_FILE = None
    PATH_TO_TRANSPORTATION_CONFIG_FILE = None
    PATH_TO_NETWORK_CONFIG_FILE = None
    TRANSPORT_TYPE = "road"

    def __init__(self, config_file):

        super().__init__(config_file)

        self._read_main_config_attributes.update(
            PATH_TO_GENERATION_CONFIG_FILE=self._set_path_to_file, PATH_TO_RESOURCE_CONFIG_FILE=self._set_path_to_file,
            PATH_TO_TRANSPORTATION_CONFIG_FILE=self._set_path_to_file,
            PATH_TO_NETWORK_CONFIG_FILE=self._set_path_to_file, TRANSPORT_TYPE=self._set_transport_type)

    def _set_transport_type(self, attr, t_type):
        self._set_among_valid_values(attr, t_type.lower(), {'road', 'rail', 'river'})

    def is_valid_config_file(self):
        return True


class SolarGHIConfigurationParser(RasterResourceConfigurationParser):

    # Fields
    TIME_ZONE = 'UTC'
    BASE_YEAR = 2018
    INTEGRATION_TIME_STEP = 30
    DAILY_KC_MONTHLY_MEAN_TOLERANCE = 2
    HOURLY_GHI_DAILY_SUM_TOLERANCE = 5

    def __init__(self, config_file):

        super().__init__(config_file)

        self._read_main_config_attributes.update(
            TIME_ZONE=self._set_time_zone, BASE_YEAR=self._set_positive_integer,
            INTEGRATION_TIME_STEP=self._set_positive_integer, DAILY_KC_MONTHLY_MEAN_TOLERANCE=self._set_tolerance,
            HOURLY_GHI_DAILY_SUM_TOLERANCE=self._set_tolerance)

    def _set_tolerance(self, attr, value):
        self._set_positive_float(attr, value)
        self._set_float_in_range(attr, value, 0, 100)


class BiomassConfigurationParser(ResourceToGenerationConfigurationParser):
    pass


class PVSystemConfigurationParser(ConfigurationParser):

    POLYGON_LAYER = None
    GHI = None
    USE_DIFFUSE_FRACTION = True
    DIFFUSE_FRACTION_MODEL = "erbs"
    DNI = None
    DHI = None
    AIR_TEMPERATURE = 20
    WIND_SPEED = 1
    ALBEDO = 0.2
    SURFACE_TILT = 0
    SURFACE_AZIMUTH = 180
    MODULE_NAME = "Canadian_Solar_CS5P_220M___2009_"
    INVERTER_NAME = 'ABB__MICRO_0_25_I_OUTD_US_208_208V__CEC_2014_'
    MODULES_PER_STRING = 1
    STRINGS_PER_INVERTER = 1
    RACKING_MODEL = "open_rack_cell_glassback"
    GROUND_COVERAGE_RATIO = 0.3
    USE_ORIENTATION_STRATEGY = False
    ORIENTATION_STRATEGY = None
    CLEAR_SKY_MODEL = "ineichen"
    SKY_DIFFUSE_MODEL = "haydavies"
    AIRMASS_MODEL = "kastenyoung1989"
    DC_MODEL = None
    AC_MODEL = None
    AOI_MODEL = None
    SPECTRAL_MODEL = None
    LOSSES_MODEL = "no_loss"
    PVWATTS_SOILING = 2
    PVWATTS_SHADING = 3
    PVWATTS_SNOW = 0
    PVWATTS_MISMATCH = 2
    PVWATTS_WIRING = 2
    PVWATTS_CONNECTIONS = 0.5
    PVWATTS_LIGHT_INDUCED_DEGRADATION = 1.5
    PVWATTS_NAMEPLATE_RATING = 1
    PVWATTS_AGE = 0
    PVWATTS_AVAILABILITY = 3
    POWER_TO_ENERGY_METHOD = 'mean'
    SAVE_OUTPUT_DC_POWER_TO = None
    SAVE_OUTPUT_AC_POWER_TO = None
    SAVE_PV_SYSTEM_FEATURES_TO = None

    def __init__(self, config_file):
        super().__init__(config_file)

        self._read_main_config_attributes.update(
            POLYGON_LAYER=self._set_path_to_layer_file, GHI=self._set_path_to_file,
            USE_DIFFUSE_FRACTION=self._set_boolean, DIFFUSE_FRACTION_MODEL=self._set_diffuse_fraction_model,
            DNI=self._set_path_to_file, DHI=self._set_path_to_file, AIR_TEMPERATURE=self._set_air_temperature,
            WIND_SPEED=self._set_wind_speed, ALBEDO=self._set_albedo, SURFACE_TILT=self._set_surface_tilt,
            SURFACE_AZIMUTH=self._set_surface_azimuth, MODULE_NAME=self._set_module_name,
            INVERTER_NAME=self._set_inverter_name, MODULES_PER_STRING=self._set_positive_integer,
            STRINGS_PER_INVERTER=self._set_positive_integer, RACKING_MODEL=self._set_racking_model,
            GROUND_COVERAGE_RATIO=self._set_gcr, USE_ORIENTATION_STRATEGY=self._set_boolean,
            ORIENTATION_STRATEGY=self._set_orientation_strategy, CLEAR_SKY_MODEL=self._set_clear_sky_model,
            SKY_DIFFUSE_MODEL=self._set_sky_diffuse_model, AIRMASS_MODEL=self._set_airmass_model,
            DC_MODEL=self._set_dc_model, AC_MODEL=self._set_ac_model, AOI_MODEL=self._set_aoi_model,
            SPECTRAL_MODEL=self._set_spectral_model, LOSSES_MODEL=self._set_losses_model,
            PVWATTS_SOILING=self._set_pvwatts_parameter, PVWATTS_SHADING=self._set_pvwatts_parameter,
            PVWATTS_SNOW=self._set_pvwatts_parameter, PVWATTS_MISMATCH=self._set_pvwatts_parameter,
            PVWATTS_WIRING=self._set_pvwatts_parameter, PVWATTS_CONNECTIONS=self._set_pvwatts_parameter,
            PVWATTS_LIGHT_INDUCED_DEGRADATION=self._set_pvwatts_parameter,
            PVWATTS_NAMEPLATE_RATING=self._set_pvwatts_parameter, PVWATTS_AGE=self._set_pvwatts_parameter,
            PVWATTS_AVAILABILITY=self._set_pvwatts_parameter, POWER_TO_ENERGY_METHOD=self._set_power_to_energy_method,
            SAVE_OUTPUT_DC_POWER_TO=self._set_table_destination_path,
            SAVE_OUTPUT_AC_POWER_TO=self._set_table_destination_path,
            SAVE_PV_SYSTEM_FEATURES_TO=self._set_table_destination_path)

    def _set_diffuse_fraction_model(self, attr, model):
        self._set_among_valid_values(attr, model.lower(), {"erbs"})
        # TODO: implement other diffuse fraction models

    def _set_air_temperature(self, attr, temp):
        try:
            self._set_path_to_file(attr, temp)
        except ConfigurationParserError:
            self._set_float_in_range(attr, temp, -60, 60)

    def _set_gcr(self, attr, gcr):
        self._set_positive_float(attr, gcr)
        self._set_float_in_range(attr, gcr, 0, 1)

    def _set_pvwatts_parameter(self, attr, value):
        self._set_float_in_range(attr, value, 0, 100)

    def _set_wind_speed(self, attr, wind):
        try:
            self._set_path_to_file(attr, wind)
        except ConfigurationParserError:
            self._set_float_in_range(attr, wind, 0, 100)

    def _set_albedo(self, attr, albedo):
        self._set_float_in_range(attr, albedo, 0, 1)

    def _set_surface_tilt(self, attr, tilt):
        self._set_float_in_range(attr, tilt, 0, 90)

    def _set_surface_azimuth(self, attr, azimuth):
        self._set_float_in_range(attr, azimuth, 0, 360)

    def _set_module_name(self, attr, name):
        self._set_among_valid_values(attr, self.name_to_key(name), VALID_MODULE_NAMES)

    def _set_inverter_name(self, attr, name):
        self._set_among_valid_values(attr, self.name_to_key(name), VALID_INVERTER_NAMES)

    def _set_racking_model(self, attr, model):
        self._set_among_valid_values(attr, model.lower(), {'open_rack_cell_glassback', 'roof_mount_cell_glassback',
                                                           'open_rack_cell_polymerback', 'insulated_back_polymerback',
                                                           'open_rack_polymer_thinfilm_steel',
                                                           '22x_concentrator_tracker'})

    def _set_orientation_strategy(self, attr, strategy):
        self._set_among_valid_values(attr, strategy.lower(), {'flat', 'south_at_latitude_tilt'})

    def _set_power_to_energy_method(self, attr, method):
        self._set_among_valid_values(attr, method.lower(), {'integration', 'mean'})

    def _set_clear_sky_model(self, attr, model):
        self._set_among_valid_values(attr, model.lower(), {'ineichen', 'haurwitz', 'simplified_solis'})

    def _set_sky_diffuse_model(self, attr, model):
        self._set_among_valid_values(attr, model.lower(), {'isotropic', 'klucher', 'haydavies', 'reindl', 'king',
                                                           'perez'})

    def _set_airmass_model(self, attr, model):
        self._set_among_valid_values(attr, model.lower(), {'simple', 'kasten1966', 'youngirvine1967', 'kastenyoung1989',
                                                           'gueymard1993', 'young1994', 'pickering2002'})

    def _set_dc_model(self, attr, model):
        self._set_among_valid_values(attr, model.lower(), {'sapm', 'desoto', 'cec', 'pvsyst', 'pvwatts'})

    def _set_ac_model(self, attr, model):
        self._set_among_valid_values(attr, model.lower(), {'snlinverter', 'adrinverter', 'pvwatts'})

    def _set_aoi_model(self, attr, model):
        self._set_among_valid_values(attr, model.lower(), {'physical', 'ashrae', 'sapm', 'no_loss'})

    def _set_spectral_model(self, attr, model):
        self._set_among_valid_values(attr, model, {'sapm', 'no_loss'})
        # TODO: add "first_solar" model, but allow precipitable water file first

    def _set_losses_model(self, attr, model):
        self._set_among_valid_values(attr, model.lower(), {'pvwatts', 'no_loss'})

    @classmethod
    def name_to_key(cls, name):
        try:
            name = name.replace(' ', '_').replace('-', '_')\
                .replace('.', '_').replace('(', '_')\
                .replace(')', '_').replace('[', '_')\
                .replace(']', '_').replace(':', '_')\
                .replace('+', '_').replace('/', '_')\
                .replace('"', '_').replace(',', '_')
        except AttributeError:
            raise PVSystemConfigurationParserError("Input is of type '%s' but must be of type 'str'" % type(
                name).__name__)

        return name

    def is_valid_config_file(self):
        return True


class MixedGenerationConfigurationParser(ConfigurationParser):

    PATH_TO_POLYGON_GENERATION_1 = None
    PATH_TO_POLYGON_GENERATION_2 = None
    GENERATION_TYPE_1 = None
    GENERATION_TYPE_2 = None
    IS_NORMALIZED = False
    SAVE_INTERSECTING_MATRIX_TO = None

    def __init__(self, config_file):
        super().__init__(config_file)

        self._read_main_config_attributes.update(
            PATH_TO_POLYGON_GENERATION_1=self._set_path_to_layer_file,
            PATH_TO_POLYGON_GENERATION_2=self._set_path_to_layer_file,
            GENERATION_TYPE_1=self._set_configuration_attribute, GENERATION_TYPE_2=self._set_configuration_attribute,
            IS_NORMALIZED=self._set_boolean, SAVE_INTERSECTING_MATRIX_TO=self._set_table_destination_path)

    def is_valid_config_file(self):
        return True


if __name__ == "__main__":
    test = MixedGenerationConfigurationParser("/home/benjamin/ownCloud/Post-doc Guyane/greece/config files/Mixed "
                                              "generation/mixed_generation.config")
    test.parse()
    print(test)
