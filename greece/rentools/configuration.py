# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'
import copy
import os
import warnings

import dateutil
import pandas as pd

from gistools.conversion import slope_to_layer
from gistools.exceptions import RasterMapError, GeoLayerError
from gistools.layer import GeoLayer, PolygonLayer
from gistools.network import RoadNode, Road
from gistools.raster import DigitalElevationModel, RasterMap
from utils.check import isfile
from utils.sys.browser import find_file

from greece.rentools import VALID_RASTER_FORMATS, CEC_MODULE_NAMES
from greece.rentools.configuration_parser import MainConfigurationParser, RoadNetworkConfigurationParser, \
    ConstraintConfigurationParser, RasterResourceConfigurationParser, NetworkConfigurationParser, \
    GridConfigurationParser, TransportationConfigurationParser, RoadTransportationConfigurationParser, \
    BiomassConfigurationParser, SolarGHIConfigurationParser, ResourceConfigurationParser, PVSystemConfigurationParser, \
    MixedGenerationConfigurationParser
from greece.rentools.exceptions import ConfigurationError, NetworkConfigurationError, MainConfigurationError, \
    ConstraintConfigurationError, ResourceConfigurationError, PVSystemConfigurationWarning
from greece.rentools.tools import get_location_from_polygon_layer
from greece.tmstools.timeseries import interp_time_series
from greece.solartools.conversion import irradiation_to_irradiance
from greece.solartools.diffuse_fraction import erbs

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


# Constants
CSV_ENCODING = 'iso_8859_1'


def str_to_float(value):
    if value == '':
        return 0
    else:
        return float(value)


class Configuration:

    def copy(self):
        return copy.deepcopy(self)

    def set_polygon_layer(self, attr, layer_file, name="layer"):
        try:
            self.__setattr__(attr, PolygonLayer(layer_file, name=name).clean_geometry(delete_invalid=True))
        except GeoLayerError:
            raise ConfigurationError("Invalid polygon layer file '%s'" % layer_file)


class MainConfiguration(Configuration):
    """ Build main configuration

    """

    dem = None
    land_use_layer = None
    land_use_attribute = None

    def __init__(self, config_file):

        self._config_parser = MainConfigurationParser(config_file).parse()

        # Set attributes
        self.crs = self._config_parser.CRS
        self.surface_crs = self._config_parser.SURFACE_CRS
        self.set_dem()
        self.set_land_use_layer()

    def set_dem(self):
        """ Set digital elevation model

        :return:
        """
        if self._config_parser.PATH_TO_DEM_FILE is not None:
            try:
                self.dem = DigitalElevationModel(self._config_parser.PATH_TO_DEM_FILE, no_data_value=-32768)
            except RasterMapError:
                raise ConfigurationError("Unable to read DEM from '%s'" % self._config_parser.PATH_TO_DEM_FILE)

    def set_land_use_layer(self):
        if self._config_parser.PATH_TO_LAND_USE_FILE is not None and self._config_parser.LAND_USE_ATTRIBUTE is not None:
            self.set_polygon_layer("land_use_layer", self._config_parser.PATH_TO_LAND_USE_FILE)
            if self._config_parser.LAND_USE_ATTRIBUTE not in self.land_use_layer.attributes():
                raise MainConfigurationError("Invalid land use attribute '%s'" % self._config_parser.LAND_USE_ATTRIBUTE)
            else:
                self.land_use_attribute = self._config_parser.LAND_USE_ATTRIBUTE


class ConstraintConfiguration(MainConfiguration):
    """ Build and store parameters related to geographic constraints

    """

    base_layer = None
    list_of_mask_layers = None
    list_of_distance_threshold_layers = None
    list_of_distance_to_resource_layers = None

    def __init__(self,  main_config_file, constraint_config_file):

        super().__init__(main_config_file)

        self._config_parser = ConstraintConfigurationParser(constraint_config_file).parse()

        # Set specific attributes
        self.compute_distance_from_centroid = self._config_parser.COMPUTE_DISTANCE_FROM_CENTROID
        self.fast_intersection_surface = self._config_parser.FAST_INTERSECTION_SURFACE_THRESHOLD
        self.min_polygon_surface = self._config_parser.MIN_POLYGON_SURFACE
        self.max_polygon_surface = self._config_parser.MAX_POLYGON_SURFACE
        self.split_method = self._config_parser.SPLIT_METHOD
        self.split_shape = self._config_parser.SPLIT_SHAPE
        self.partition_options = dict(disaggregation_factor=self._config_parser.DISAGGREGATION_FACTOR,
                                      precision=self._config_parser.METRIC_PRECISION, recursive=False,
                                      objtype=self._config_parser.METIS_OBJTYPE, contig=True,
                                      ncuts=self._config_parser.METIS_NCUTS, iptype=self._config_parser.METIS_IPTYPE,
                                      rtype=self._config_parser.METIS_RTYPE)
        self.compute_shape_factor = self._config_parser.COMPUTE_SHAPE_FACTOR
        self.use_convex_hull = self._config_parser.USE_CONVEX_HULL_SHAPE
        self.compute_dem_statistics = self._config_parser.COMPUTE_DEM_STATISTICS
        self.extract_land_use = self._config_parser.EXTRACT_LAND_USE
        self.destination_path = dict(layer=self._config_parser.SAVE_POLYGON_LAYER_TO,
                                     table=self._config_parser.SAVE_POLYGON_TABLE_TO)
        self.set_base_layer()
        self.set_list_of_distance_threshold_layers()
        self.set_list_of_mask_layers()
        self.set_list_of_distance_to_polygon_layers()

    def set_base_layer(self):
        if self._config_parser.PATH_TO_BASE_LAYER_FILE is not None and self._config_parser.BASE_LAYER_METHOD == "file":
            self.set_polygon_layer("base_layer", self._config_parser.PATH_TO_BASE_LAYER_FILE)
        elif self._config_parser.SLOPE_THRESHOLD is not None and self._config_parser.SIMPLIFY_TOLERANCE is not None \
                and self._config_parser.BASE_LAYER_METHOD == "slope":
            base_layer = slope_to_layer(self.dem, self._config_parser.SLOPE_THRESHOLD,
                                        min_connection=self._config_parser.SIEVE_FILTER_MINIMUM_CONNECTION,
                                        simplify_tolerance=self._config_parser.SIMPLIFY_TOLERANCE,
                                        is_8_connected=self._config_parser.IS_8_CONNECTED)
            self.base_layer = base_layer.clean_geometry(delete_invalid=True)

    def set_list_of_distance_to_polygon_layers(self):
        """ Set list of layers from which distance to final polygon must be computed

        :return:
        """
        self.list_of_distance_to_resource_layers = []
        if self._config_parser.PATH_TO_DISTANCE_FROM_POLYGON_TO_LAYER_DIRECTORY is not None and \
                self._config_parser.PATH_TO_DISTANCE_FROM_POLYGON_TO_LAYER_CONFIG_FILE is not None:
            alist = self._get_list_from_sub_config_file(
                self._config_parser.PATH_TO_DISTANCE_FROM_POLYGON_TO_LAYER_DIRECTORY,
                self._config_parser.PATH_TO_DISTANCE_FROM_POLYGON_TO_LAYER_CONFIG_FILE, no_param=True)
            self.list_of_distance_to_resource_layers.extend(alist[::2])

    def set_list_of_distance_threshold_layers(self):
        """ Set list of layers corresponding to distance threshold

        :return:
        """
        self.list_of_distance_threshold_layers = []
        if self._config_parser.PATH_TO_DISTANCE_THRESHOLD_DIRECTORY is not None and \
                self._config_parser.PATH_TO_DISTANCE_THRESHOLD_CONFIG_FILE is not None:
            self.list_of_distance_threshold_layers.extend(self._get_list_from_sub_config_file(
                self._config_parser.PATH_TO_DISTANCE_THRESHOLD_DIRECTORY,
                self._config_parser.PATH_TO_DISTANCE_THRESHOLD_CONFIG_FILE))

    def set_list_of_mask_layers(self):
        """ Set list of layers corresponding to mask

        :return:
        """
        self.list_of_mask_layers = []
        if self._config_parser.PATH_TO_MASK_DIRECTORY is not None and self._config_parser.PATH_TO_MASK_CONFIG_FILE is \
                not None:
            self.list_of_mask_layers.extend(self._get_list_from_sub_config_file(
                self._config_parser.PATH_TO_MASK_DIRECTORY, self._config_parser.PATH_TO_MASK_CONFIG_FILE))

    ###################
    # Protected methods
    @staticmethod
    def _get_list_from_sub_config_file(path_to_directory, path_to_config_file, no_param=False):

        arg_list = []

        try:
            with open(path_to_config_file, encoding=CSV_ENCODING) as config_file:
                temp = config_file.read().splitlines()
        except UnicodeDecodeError:
            raise ConstraintConfigurationError("Encoding of file '%s' should be '%s'" % (path_to_config_file,
                                                                                         CSV_ENCODING))

        for line_count, line in enumerate(temp[1::]):
            if not line.startswith("#"):
                if no_param:
                    line += ","
                line_count += 2
                try:
                    name, rel_path, attr_name, attr_value, param_value = line.split(sep=",")
                except ValueError:
                    raise ConstraintConfigurationError("Wrong format for config file '%s'" % config_file.name)
                abs_path = os.path.join(path_to_directory, rel_path)
                try:
                    geo_layer = GeoLayer(abs_path, name=name)
                except GeoLayerError:
                    raise ConstraintConfigurationError("Invalid path to geo file in line %d of file '%s'" % (
                        line_count, config_file.name))
                if attr_name != '':
                    if attr_name in geo_layer.attributes():
                        try:
                            # Only compare and save ascii characters using unidecode module
                            # geo_layer[attr_name] = [unidecode(str(attr_val)) for attr_val in geo_layer[attr_name]]
                            # geo_layer = geo_layer[geo_layer[attr_name] == unidecode(attr_value)]
                            geo_layer = geo_layer[geo_layer[attr_name] == attr_value]
                        except GeoLayerError:
                            raise ConstraintConfigurationError("Invalid attribute value in line %d of file '%s'"
                                                               % (line_count, config_file.name))
                    else:
                        raise ConstraintConfigurationError("Invalid attribute name in line %d of file '%s'" % (
                            line_count, config_file.name))
                # Get parameter value
                try:
                    param_value = str_to_float(param_value)
                except (ValueError, TypeError):
                    raise ConstraintConfigurationError("Invalid parameter value in line %d of file '%s'" %
                                                       (line_count, config_file.name))

                # Append lines_ and buffer to arg list
                arg_list.extend([geo_layer, param_value])

        return arg_list


class ResourceConfiguration(ConstraintConfiguration):

    contour_interval = None

    def __init__(self, main_config_file, resource_config_file):

        super().__init__(main_config_file, resource_config_file)
        self._config_parser = ResourceConfigurationParser(resource_config_file).parse()

        # Set attributes
        self.destination_path.update(resource_table=self._config_parser.SAVE_RESOURCE_TABLE_TO)
        self.identify_resource_contour_zones = self._config_parser.IDENTIFY_RESOURCE_CONTOUR_ZONES
        self.contour_interval_type = self._config_parser.CONTOUR_INTERVAL_TYPE
        self.main_percentile_range = self._config_parser.MAIN_PERCENTILE_RANGE
        self.use_resource_generator = self._config_parser.USE_RESOURCE_GENERATOR
        self.resource_generator = self._config_parser.RESOURCE_GENERATOR

        self.set_contour_interval()

    def set_contour_interval(self):
        if self.contour_interval_type == 'relative':
            self.contour_interval = self._config_parser.CONTOUR_INTERVAL_VALUE / 100
        else:
            self.contour_interval = self._config_parser.CONTOUR_INTERVAL_VALUE


class RasterResourceConfiguration(ResourceConfiguration):
    """ Build and store parameters from configuration parser

    """

    resource_raster = None

    def __init__(self, main_config_file, resource_config_file):

        super().__init__(main_config_file, resource_config_file)
        self._config_parser = RasterResourceConfigurationParser(resource_config_file).parse()

        # Set specific attributes
        self.all_touched = self._config_parser.ALL_TOUCHED
        self.is_surface_weighted = self._config_parser.SURFACE_WEIGHTED
        self.set_resource_raster()

    def set_resource_raster(self):
        if self._config_parser.PATH_TO_RESOURCE is not None:
            if os.path.isdir(self._config_parser.PATH_TO_RESOURCE) and self._config_parser.RASTER_FORMAT is not None:
                self.resource_raster = []
                set_of_files = find_file(VALID_RASTER_FORMATS[self._config_parser.RASTER_FORMAT],
                                         self._config_parser.PATH_TO_RESOURCE, sort=True)
                if len(set_of_files) == 0:
                    raise ResourceConfigurationError("No raster format '%s' found in directory '%s'" % (
                        self._config_parser.RASTER_FORMAT, self._config_parser.PATH_TO_RESOURCE))
                for file in set_of_files:
                    try:
                        raster_map = RasterMap(file, no_data_value=self._config_parser.NO_DATA_VALUE)
                    except RasterMapError:
                        raise ResourceConfigurationError("Raster file '%s' cannot be read" % file)
                    if self._config_parser.RESAMPLING_FACTOR is not None:
                        raster_map = raster_map.gdal_resample(self._config_parser.RESAMPLING_FACTOR)
                    self.resource_raster.append(raster_map)

            elif isfile(self._config_parser.PATH_TO_RESOURCE):
                try:
                    self.resource_raster = RasterMap(self._config_parser.PATH_TO_RESOURCE,
                                                     no_data_value=self._config_parser.NO_DATA_VALUE)
                except RasterMapError:
                    raise ResourceConfigurationError("Raster file '%s' cannot be read" %
                                                     self._config_parser.PATH_TO_RESOURCE)
                if self._config_parser.RESAMPLING_FACTOR is not None:
                    self.resource_raster = self.resource_raster.gdal_resample(self._config_parser.RESAMPLING_FACTOR)


class SolarGHIConfiguration(RasterResourceConfiguration):
    """ Implement config for solar resource

    """
    def __init__(self, main_config_file, solar_config_file):

        super().__init__(main_config_file, solar_config_file)
        self._config_parser = SolarGHIConfigurationParser(solar_config_file).parse()

        # Set attributes
        self.accuracy = "%d min" % self._config_parser.INTEGRATION_TIME_STEP
        self.time_zone = self._config_parser.TIME_ZONE
        self.base_year = self._config_parser.BASE_YEAR
        self.daily_kc_tolerance = self._config_parser.DAILY_KC_MONTHLY_MEAN_TOLERANCE / 100
        self.hourly_ghi_tolerance = self._config_parser.HOURLY_GHI_DAILY_SUM_TOLERANCE / 100


class BiomassGenerationConfiguration(ConstraintConfiguration):
    """ Implement config for biomass power plants

    """
    pass


class BiomassResourceConfiguration(RasterResourceConfiguration):
    """ Implement config for biomass resource

    """
    pass


class NetworkConfiguration(MainConfiguration):
    """ Network configuration

    """

    edge_layer = None
    node_layer = None

    edge_class = None
    node_class = None

    def __init__(self, main_config_file, network_config_file):

        super().__init__(main_config_file)
        self._config_parser = NetworkConfigurationParser(network_config_file).parse()

        # Set attributes
        self.find_disconnected_islands_and_fix = self._config_parser.FIND_DISCONNECTED_ISLANDS_AND_FIX
        self.find_and_fix_method = self._config_parser.FIND_AND_FIX_METHOD
        self.find_and_fix_tolerance = self._config_parser.FIND_AND_FIX_TOLERANCE
        self.match_edge_nodes = self._config_parser.MATCH_EDGE_NODES
        self.add_z_dimension = self._config_parser.ADD_Z_DIMENSION
        self.node_tolerance = self._config_parser.NODE_TOLERANCE
        self.edge_resolution = self._config_parser.EDGE_RESOLUTION
        self.set_edge_layer()
        self.set_node_layer()

    @staticmethod
    def _get_attribute_values(attr_file, layer):

        attribute, attribute_value, value = [], [], []

        try:
            with open(attr_file, encoding=CSV_ENCODING) as config_file:
                temp = config_file.read().splitlines()
        except UnicodeDecodeError:
            raise NetworkConfigurationError("Encoding of file '%s' should be '%s'" % (attr_file, CSV_ENCODING))

        if len(temp) <= 1:
            raise NetworkConfigurationError("File '%s' is empty" % config_file.name)

        for line_count, line in enumerate(temp[1::]):
            line_count += 2
            try:
                attr_name, attr_value, param_value = line.split(sep=",")
            except ValueError:
                raise NetworkConfigurationError("Wrong format for network attribute file '%s'" % config_file.name)
            if attr_name not in layer.attributes():
                raise NetworkConfigurationError("Wrong attribute name in line %d of file '%s'" % (line_count,
                                                                                                  config_file.name))
            if attr_value not in set(layer[attr_name]):
                raise NetworkConfigurationError("Wrong attribute value in line %d of file '%s' "
                                                % (line_count, config_file.name))
            # If parameter is numeric, convert it
            try:
                param_value = str_to_float(param_value)
            except ValueError:
                pass

            attribute.append(attr_name)
            attribute_value.append(attr_value)
            value.append(param_value)

        attribute = list(set(attribute))
        if len(attribute) > 1:
            raise NetworkConfigurationError("Attribute name must be unique in file '%s'" % config_file.name)

        return attribute[0], {attr_val: val for attr_val, val in zip(attribute_value, value)}

    def set_edge_direction(self):
        """ Set direction of edges in lines_

        :return:
        """
        if self._config_parser.PATH_TO_DIRECTION_CONFIG_FILE is not None:
            attr_name, direction_dict = self._get_attribute_values(self._config_parser.PATH_TO_DIRECTION_CONFIG_FILE,
                                                                   self.edge_layer)
            self.edge_layer.set_direction(attr_name, direction_dict)

    def set_edge_layer(self):
        """ Initiate edge lines_

        :return:
        """
        try:
            self.edge_layer = self.edge_class(self._config_parser.PATH_TO_EDGE_FILE)
        except GeoLayerError:
            raise NetworkConfigurationError("Invalid edge layer file '%s'" % self._config_parser.PATH_TO_EDGE_FILE)

        # Set edge directions
        self.set_edge_direction()

    def set_node_layer(self):
        """ Initiate node lines_

        :return:
        """
        if self._config_parser.PATH_TO_NODE_FILE is not None:
            try:
                self.node_layer = self.node_class(self._config_parser.PATH_TO_NODE_FILE)
            except GeoLayerError:
                raise NetworkConfigurationError("Invalid node layer file '%s'" % self._config_parser.PATH_TO_NODE_FILE)
        else:
            try:
                self.node_layer = self.edge_layer.get_nodes()
            except GeoLayerError as e:
                raise NetworkConfigurationError("Unable to retrieve nodes from edges:\n%s" % e)


class GridConfiguration(NetworkConfiguration):
    """

    """

    def __init__(self, main_config_file, grid_config_file):

        super().__init__(main_config_file, grid_config_file)
        self._config_parser = GridConfigurationParser(grid_config_file).parse()

        # Set specific class attributes
        self.model = self._config_parser.MODEL


class RoadNetworkConfiguration(NetworkConfiguration):
    """

    """
    edge_class = Road
    node_class = RoadNode

    def __init__(self, main_config_file, road_network_config_file):

        super().__init__(main_config_file, road_network_config_file)
        self._config_parser = RoadNetworkConfigurationParser(road_network_config_file).parse()

        # Set attributes
        self.set_road_max_speed()
        self.set_road_rolling_coefficient()
        self.set_road_rollover_criterion()
        self.set_node_max_speed()

    def set_node_max_speed(self):
        """ Set max allowed speed at road intersection

        :return:
        """
        if self._config_parser.PATH_TO_NODE_SPEED_CONFIG_FILE is not None:
            attr_name, node_speed_dict = self._get_attribute_values(
                self._config_parser.PATH_TO_NODE_SPEED_CONFIG_FILE, self.node_layer)
            self.node_layer.set_max_speed(attr_name, node_speed_dict, self._config_parser.SPEED_FORMAT)

    def set_road_max_speed(self):
        """ Set road maximum allowed speed

        :return:
        """
        if self._config_parser.PATH_TO_SPEED_LIMIT_CONFIG_FILE is not None:
            attr_name, speed_dict = self._get_attribute_values(self._config_parser.PATH_TO_SPEED_LIMIT_CONFIG_FILE,
                                                               self.edge_layer)
            self.edge_layer.set_max_speed(attr_name, speed_dict, self._config_parser.SPEED_FORMAT)

    def set_road_rolling_coefficient(self):
        """ Set road rolling coefficient

        :return:
        """
        if self._config_parser.PATH_TO_ROLLING_COEFFICIENT_CONFIG_FILE is not None:
            attr_name, rolling_coeff_dict = self._get_attribute_values(
                self._config_parser.PATH_TO_ROLLING_COEFFICIENT_CONFIG_FILE, self.edge_layer)
            self.edge_layer.set_rolling_coefficient(attr_name, rolling_coeff_dict)

    def set_road_rollover_criterion(self):
        """ Set road rollover criterion

        :return:
        """
        if self._config_parser.PATH_TO_ROLLOVER_CRITERION_CONFIG_FILE is not None:
            attr_name, rollover_criterion_dict = self._get_attribute_values(
                self._config_parser.PATH_TO_ROLLOVER_CRITERION_CONFIG_FILE, self.edge_layer)
            self.edge_layer.set_rollover_criterion(attr_name, rollover_criterion_dict)


class TransportationConfiguration(Configuration):
    """ Build transportation configuration

    """

    def __init__(self, transportation_config_file):

        self._config_parser = TransportationConfigurationParser(transportation_config_file).parse()

        # Set attribute
        self.use_centroid_projection = self._config_parser.USE_CENTROID_PROJECTION


class RoadTransportationConfiguration(RoadNetworkConfiguration, TransportationConfiguration):
    """ Build road transportation configuration

    """

    def __init__(self, main_config_file, road_network_config_file, road_transportation_config_file):

        RoadNetworkConfiguration.__init__(self, main_config_file, road_network_config_file)
        TransportationConfiguration.__init__(self, road_transportation_config_file)

        self._config_parser = RoadTransportationConfigurationParser(road_transportation_config_file).parse()

        # Set attributes
        self.time_format = self._config_parser.TIME_FORMAT
        self.tare_weight = self._config_parser.TARE_WEIGHT
        self.gross_weight = self._config_parser.GROSS_WEIGHT
        self.gross_hp = self._config_parser.GROSS_HORSE_POWER
        self.frontal_area = self._config_parser.FRONTAL_AREA
        self.engine_efficiency = self._config_parser.ENGINE_EFFICIENCY
        self.fuel_energy_density = self._config_parser.FUEL_VOLUMETRIC_ENERGY_DENSITY
        self.uphill_hp = self._config_parser.UPHILL_HORSE_POWER_RATE
        self.downhill_hp = self._config_parser.DOWNHILL_HORSE_POWER_RATE
        self.drag_resistance = self._config_parser.DRAG_RESISTANCE
        self.mass_correction_factor = self._config_parser.MASS_CORRECTION_FACTOR
        self.acceleration_rate = self._config_parser.ACCELERATION_RATE
        self.deceleration_rate = -1 * self._config_parser.DECELERATION_RATE


class BiomassConfiguration(Configuration):
    """ Implement config for biomass (generation, resource & transport)

    """
    _transport_class = dict(road=RoadTransportationConfiguration, river=None, rail=None)

    def __init__(self, main_config_file, biomass_config_file):

        self._config_parser = BiomassConfigurationParser(biomass_config_file).parse()

        # Set attributes
        self.transport_type = self._config_parser.TRANSPORT_TYPE
        self.biomass_generation = BiomassGenerationConfiguration(main_config_file,
                                                                 self._config_parser.PATH_TO_GENERATION_CONFIG_FILE)
        self.biomass_resource = BiomassResourceConfiguration(main_config_file,
                                                             self._config_parser.PATH_TO_RESOURCE_CONFIG_FILE)

        # Transport
        self.biomass_transport = \
            self._transport_class[self.transport_type](main_config_file,
                                                       self._config_parser.PATH_TO_NETWORK_CONFIG_FILE,
                                                       self._config_parser.PATH_TO_TRANSPORTATION_CONFIG_FILE)


class MixedGenerationConfiguration(MainConfiguration):
    """ Implement config for mixed generation

    """
    polygon_generation_1 = None
    polygon_generation_2 = None

    def __init__(self, main_config_file, mixed_generation_config_file):
        super().__init__(main_config_file)
        self._config_parser = MixedGenerationConfigurationParser(mixed_generation_config_file).parse()

        # Set attributes
        self.set_polygon_layer("polygon_generation_1", self._config_parser.PATH_TO_POLYGON_GENERATION_1,
                               name=self._config_parser.GENERATION_TYPE_1)
        self.set_polygon_layer("polygon_generation_2", self._config_parser.PATH_TO_POLYGON_GENERATION_2,
                               name=self._config_parser.GENERATION_TYPE_2)
        self.destination_path = self._config_parser.SAVE_INTERSECTING_MATRIX_TO
        self.is_normalized = self._config_parser.IS_NORMALIZED


class PVSystemConfiguration(Configuration):
    """ Implement config for PV system model

    """
    polygon_layer = None
    ghi = None
    dni = None
    dhi = None
    air_temperature = None
    wind_speed = None
    surface_orientation = None
    aoi_model = None
    spectral_model = None
    losses_parameters = None

    def __init__(self, pv_model_config_file):

        self._config_parser = PVSystemConfigurationParser(pv_model_config_file).parse()

        # Set attributes
        self.set_polygon_layer("polygon_layer", self._config_parser.POLYGON_LAYER)
        self.location = get_location_from_polygon_layer(self.polygon_layer, "Elevation mean")
        self.set_ghi()
        self.set_dni_and_dhi()
        self.power_to_energy_method = self._config_parser.POWER_TO_ENERGY_METHOD
        self.albedo = self._config_parser.ALBEDO
        self.module_name = self._config_parser.MODULE_NAME
        self.inverter_name = self._config_parser.INVERTER_NAME
        self.modules_per_string = self._config_parser.MODULES_PER_STRING
        self.strings_per_inverter = self._config_parser.STRINGS_PER_INVERTER
        self.racking_model = self._config_parser.RACKING_MODEL
        self.ground_coverage_ratio = self._config_parser.GROUND_COVERAGE_RATIO
        self.clear_sky_model = self._config_parser.CLEAR_SKY_MODEL
        self.sky_diffuse_model = self._config_parser.SKY_DIFFUSE_MODEL
        self.airmass_model = self._config_parser.AIRMASS_MODEL
        self.dc_model = self._config_parser.DC_MODEL
        self.ac_model = self._config_parser.AC_MODEL
        self.set_aoi_model()
        self.set_spectral_model()
        self.losses_model = self._config_parser.LOSSES_MODEL
        self.destination_path = dict(dc=self._config_parser.SAVE_OUTPUT_DC_POWER_TO,
                                     ac=self._config_parser.SAVE_OUTPUT_AC_POWER_TO,
                                     features=self._config_parser.SAVE_PV_SYSTEM_FEATURES_TO)
        self.set_climatic_parameters()
        self.set_surface_orientation()
        self.set_losses_parameters()

    def set_aoi_model(self):
        """ Set AOI model

        :return:
        """
        if self._config_parser.AOI_MODEL is None and self.module_name in CEC_MODULE_NAMES:
            self.aoi_model = "physical"
            warnings.warn("AOI model set to 'physical': inferring model from CEC module is not possible",
                          PVSystemConfigurationWarning)
        else:
            self.aoi_model = self._config_parser.AOI_MODEL

    def set_spectral_model(self):
        """ Set spectral model

        :return:
        """
        if self._config_parser.SPECTRAL_MODEL is None and self.module_name in CEC_MODULE_NAMES:
            self.spectral_model = "no_loss"
            warnings.warn("Spectral model set to 'no_loss': first_solar requires precipitable water data",
                          PVSystemConfigurationWarning)
        else:
            self.spectral_model = self._config_parser.SPECTRAL_MODEL

    def set_dni_and_dhi(self):
        """ Set DNI and DHI

        :return:
        """
        if self._config_parser.USE_DIFFUSE_FRACTION:
            if self._config_parser.DIFFUSE_FRACTION_MODEL == "erbs":
                df = [erbs(ghi, location) for ghi, location in zip(self.ghi, self.location)]
                self.dni = [ds["dni"] for ds in df]
                self.dhi = [ds["dhi"] for ds in df]
            else:
                pass
        else:
            pass
        # self.dni = pd.read_csv(self._config_parser.DNI, parse_dates=True, date_parser=pd.DatetimeIndex, index_col=0)
        # self.dhi = pd.read_csv(self._config_parser.DHI, parse_dates=True, date_parser=pd.DatetimeIndex, index_col=0)
        # if self.dni.shape != self.ghi.shape or self.dni.shape != self.ghi.shape:
        #     raise PVSystemConfigurationError("Shape of DNI ({}) or DHI ({}) must be the same as GHI ({})".format(
        #         self.dni.shape, self.dhi.shape, self.ghi.shape))

    def set_climatic_parameters(self):
        """ Set air temperature, wind speed and albedo

        :return:
        """
        for attr, param in zip(["air_temperature", "wind_speed"], [self._config_parser.AIR_TEMPERATURE,
                               self._config_parser.WIND_SPEED]):
            try:
                df = pd.read_csv(param, parse_dates=True, date_parser=dateutil.parser.parse, index_col=0)
                out = [interp_time_series(df[col], ghi.index) for col, ghi in zip(df, self.ghi)]
                # if out.shape != self.ghi.shape:
                #     raise PVSystemConfigurationError("Shape of '{}' ({}) is not the same as shape of "
                #                                      "GHI ({})".format(param, out.shape, self.ghi.shape))
            except ValueError:
                out = [pd.Series(data=[param] * len(ghi), index=ghi.index) for ghi in self.ghi]

            self.__setattr__(attr, out)

    def set_ghi(self):
        """ Set GHI (convert irradiance from irradiation)

        :return:
        """
        ghi = pd.read_csv(self._config_parser.GHI, parse_dates=True, date_parser=dateutil.parser.parse, index_col=0)
        self.ghi = [irradiation_to_irradiance(ghi[col], loc) for col, loc in zip(ghi, self.location)]

    def set_losses_parameters(self):
        """ Set PVWATTS losses parameters

        :return:
        """
        self.losses_parameters = dict(soiling=self._config_parser.PVWATTS_SOILING,
                                      shading=self._config_parser.PVWATTS_SHADING,
                                      snow=self._config_parser.PVWATTS_SNOW,
                                      mismatch=self._config_parser.PVWATTS_MISMATCH,
                                      wiring=self._config_parser.PVWATTS_WIRING,
                                      connections=self._config_parser.PVWATTS_CONNECTIONS,
                                      lid=self._config_parser.PVWATTS_LIGHT_INDUCED_DEGRADATION,
                                      nameplate_rating=self._config_parser.PVWATTS_NAMEPLATE_RATING,
                                      age=self._config_parser.PVWATTS_AGE,
                                      availability=self._config_parser.PVWATTS_AVAILABILITY)

    def set_surface_orientation(self):
        """ Set surface orientation according to values or strategy

        :return:
        """
        if self._config_parser.USE_ORIENTATION_STRATEGY:
            if self._config_parser.ORIENTATION_STRATEGY == "flat":
                self.surface_orientation = pd.DataFrame({'surface_tilt': [0] * len(self.polygon_layer),
                                                         'surface_azimuth': [180] * len(self.polygon_layer)})

            elif self._config_parser.ORIENTATION_STRATEGY == "south_at_latitude_tilt":
                self.surface_orientation = pd.DataFrame({'surface_tilt': [loc.latitude for loc in self.location],
                                                         'surface_azimuth': [180] * len(self.polygon_layer)})

            else:
                pass

        else:
            self.surface_orientation = \
                pd.DataFrame({'surface_tilt': [self._config_parser.SURFACE_TILT] * len(self.polygon_layer),
                              'surface_azimuth': [self._config_parser.SURFACE_AZIMUTH] * len(self.polygon_layer)})


if __name__ == "__main__":
    import numpy as np
    test = SolarGHIConfiguration("/home/benjamin/ownCloud/Post-doc Guyane/GREECE model/Config files/Main "
                                 "configuration/main.config", "/home/benjamin/ownCloud/Post-doc Guyane/GREECE model/"
                                                              "Config files/Solar GHI/solar.config")
    length = 0
    for layer in test.list_of_mask_layers[::2]:
        print("%s, length=%d" % (layer.name, len(layer)))
        length += len(layer)
    print("\nTotal length = %d\n" % length)
    print("Length of base layer: %d" % len(test.base_layer))
    print("Area of base layer: %.3f" % (np.sum(test.base_layer.area)))
    # test = MixedGenerationConfiguration("/home/benjamin/ownCloud/Post-doc Guyane/GREECE model/Config files/Mixed "
    #                                     "generation/mixed_generation.config")
