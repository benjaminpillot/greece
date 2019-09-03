# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'
import os
from abc import ABCMeta, abstractmethod

from numpy import sum as npsum
from numpy import zeros as npzeros
from pandas import DataFrame, date_range
from pvlib.modelchain import ModelChain
from pvlib.pvsystem import PVSystem
from gistools.exceptions import GeoLayerEmptyError
from gistools.network import RoadNetwork, find_all_disconnected_edges_and_fix
from utils.check import protected_property
from utils.sys.timer import broadcast_event

from greece.rentools import VALID_LAYER_DRIVERS, SANDIA_MODULE_DATABASE, CEC_MODULE_DATABASE, CEC_INVERTER_DATABASE
from greece.rentools.configuration import RoadTransportationConfiguration, BiomassConfiguration, \
    PVSystemConfiguration, MixedGenerationConfiguration
from greece.rentools.exceptions import SpatialExtractionModelError, SpatialRasterResourceModelError
from greece.rentools.resource import RasterResourceMap, PolygonMap, SolarGHIResourceMap
from greece.solartools.conversion import irradiance_to_irradiation

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


class Model(metaclass=ABCMeta):

    def __init__(self, configuration):
        self.configuration = configuration

    @abstractmethod
    def run(self, *args, **kwargs):
        pass

    @broadcast_event("Saving results", message_level=1)
    def save_results(self, *args, **kwargs):
        pass


class GeoModel(Model):

    @property
    def dem(self):
        return self.configuration.dem.to_crs(self.configuration.crs)

    def run(self, *args, **kwargs):
        pass


# Resource
class SpatialExtractionModel(GeoModel, metaclass=ABCMeta):
    """ Abstract class for spatial extraction of energy resource/generation polygons

    """

    # Main attributes
    polygon_map = None

    @abstractmethod
    def _init_polygon_map_instance(self):
        self.polygon_map = PolygonMap(self.configuration.base_layer, self.configuration.crs, self.configuration.dem,
                                      self.configuration.land_use_layer, self.configuration.surface_crs,
                                      self.configuration.compute_distance_from_centroid)

    @broadcast_event("Loading constraint layers")
    def init_polygon_map_instance(self):
        self._init_polygon_map_instance()
        self.polygon_map.add_layer_mask(*self.configuration.list_of_mask_layers)
        self.polygon_map.add_layer_distance_threshold(*self.configuration.list_of_distance_threshold_layers)
        self.polygon_map.add_distance_to_polygon(*self.configuration.list_of_distance_to_resource_layers)

    @broadcast_event("Extracting polygons", message_level=1, no_time=True)
    def extract_polygons(self, *args):
        """ Retrieve resource polygons from resource map

        Retrieve resource polygons from corresponding
        resource map with respect to configuration
        :param args: optional arguments of the "extract_polygons" method of PolygonMap instance
        :return:
        """
        # Init polygon map and extract polygons
        self.init_polygon_map_instance()
        try:
            self.polygon_map.extract_polygons(
                self.configuration.fast_intersection_surface, self.configuration.min_polygon_surface,
                self.configuration.max_polygon_surface, self.configuration.split_method,
                self.configuration.split_shape, self.configuration.partition_options,
                self.configuration.compute_shape_factor, self.configuration.use_convex_hull,
                self.configuration.extract_land_use, self.configuration.land_use_attribute,
                self.configuration.compute_dem_statistics, *args)
        except GeoLayerEmptyError:
            raise SpatialExtractionModelError("No available polygons with given configuration")

    def run(self):
        """ Run model

        :return:
        """
        self.extract_polygons()
        self.save_results()

    def save_results(self):
        """ Save results to geo & table files

        :return:
        """
        super().save_results()

        if self.configuration.destination_path["layer"] is not None:
            self.polygons.to_file(self.configuration.destination_path["layer"], VALID_LAYER_DRIVERS[os.path.splitext(
                self.configuration.destination_path["layer"])[1]])

        if self.configuration.destination_path["table"] is not None:
            self.polygons.index += 1  # Start index at 1 in csv file
            self.polygons.to_csv(self.configuration.destination_path["table"],
                                 attributes=[attr for attr in self.polygons.attributes() if attr != "geometry"],
                                 float_format="%.2f")

    @property
    def polygons(self):
        if self.polygon_map.polygons is not None:
            return self.polygon_map.polygons
        else:
            raise SpatialExtractionModelError("Polygons have not been extracted yet")


class SpatialGenerationModel(SpatialExtractionModel):
    """ Class for modeling energy generation

    """

    @broadcast_event("Initializing generation model", message_level=1)
    def __init__(self, configuration):
        super().__init__(configuration)

    def _init_polygon_map_instance(self):
        super()._init_polygon_map_instance()

    def extract_polygons(self, *args):
        super().extract_polygons(*args)

    def save_results(self):
        super().save_results()


class SpatialRasterResourceModel(SpatialExtractionModel):
    """ Class for modeling energy resource

    """

    _resource_map_class = RasterResourceMap

    @broadcast_event("Initiating resource model", message_level=1)
    def __init__(self, configuration):
        super().__init__(configuration)

    def _init_polygon_map_instance(self):
        # TODO: let the resource being a LAYER too
        if self.configuration.resource_raster is None:
            super()._init_polygon_map_instance()
        else:
            self.polygon_map = self._resource_map_class(self.configuration.resource_raster,
                                                        self.configuration.base_layer,
                                                        self.configuration.crs,
                                                        self.configuration.dem,
                                                        self.configuration.land_use_layer,
                                                        self.configuration.surface_crs,
                                                        self.configuration.compute_distance_from_centroid)

    def extract_polygons(self, *args):

        super().extract_polygons(self.configuration.is_surface_weighted,
                                 self.configuration.all_touched,
                                 self.configuration.identify_resource_contour_zones,
                                 self.configuration.contour_interval_type,
                                 self.configuration.contour_interval,
                                 self.configuration.main_percentile_range,
                                 self.configuration.use_resource_generator,
                                 self.configuration.resource_generator, *args)

    def save_results(self):

        super().save_results()

        # Save resource
        if self.configuration.destination_path["resource_table"] is not None:
            self.resource.to_csv(self.configuration.destination_path["resource_table"], float_format="%.2f",
                                 index=True)

    @property
    def resource(self):
        if self.polygon_map.polygon_resource is not None:
            return self.polygon_map.polygon_resource
        else:
            raise SpatialRasterResourceModelError("No resource has been extracted yet")


class SolarGHIModel(SpatialRasterResourceModel):

    _resource_map_class = SolarGHIResourceMap

    def extract_polygons(self):

        super().extract_polygons(self.configuration.time_zone,
                                 self.configuration.accuracy,
                                 self.configuration.base_year,
                                 self.configuration.daily_kc_tolerance,
                                 self.configuration.hourly_ghi_tolerance)


class BiomassResourceModel(SpatialRasterResourceModel):

    def generate_resource(self):
        pass


class TransportationModel(GeoModel, metaclass=ABCMeta):

    network_model = None
    network_model_class = None

    fuel_consumption = dict(empty={}, loaded={})
    travel_time = dict(empty={}, loaded={})

    _layer_from = None
    _layer_to = None
    _points_from = None
    _points_to = None
    _weights = dict(fuel_empty=[], fuel_loaded=[], time_empty=[], time_loaded=[])
    _path_type = dict(fuel={True: "fuel_empty", False: "fuel_loaded"}, time={True: "time_empty", False: "time_loaded"})

    @broadcast_event("Initiating transportation model", message_level=1, no_time=True)
    def __init__(self, configuration):
        super().__init__(configuration)
        self.network_model = self.network_model_class(configuration)
        self._set_fuel_consumption()
        self._set_travel_time()

    @abstractmethod
    def _set_fuel_consumption(self):
        pass

    @abstractmethod
    def _set_travel_time(self):
        pass

    def get_shortest_path(self, idx_from, idx_to, ptype="fuel", is_empty=False):
        """ Get shortest path

        :param idx_from: idx of origin layer
        :param idx_to: idx of destination layer
        :param ptype: path type ("time" or "fuel")
        :param is_empty: is vehicle loaded or empty ?
        :return:
        """
        pt_from = self._points_from.geometry[idx_from]
        pt_to = self._points_to.geometry[idx_to]
        self.network_model.network.build_graph(*self._weights[self._path_type[ptype][is_empty]])

        return self.network_model.network.get_shortest_path(pt_from, pt_to), \
            self.network_model.network.get_shortest_path(pt_to, pt_from)

    def get_shortest_path_length(self):
        """ Get shortest path length

        :return:
        """
        sp_matrix = npzeros((len(self._points_from), len(self._points_to)))
        fuel_path = {'name': 'fuel consumption', 'from_to': sp_matrix.copy(), 'to_from': sp_matrix.copy()}
        travel_time_path = {'name': 'time', 'from_to': sp_matrix.copy(), 'to_from': sp_matrix.copy()}

        # Fuel and travel time shortest path (empty)
        for path, weight in zip([fuel_path, travel_time_path],
                                [self._weights["fuel_empty"], self._weights["time_empty"]]):
            self.network_model.network.build_graph(*weight)
            for n, point in enumerate(self._points_from.geometry):
                path["from_to"][n, :] = self.network_model.network.get_shortest_path_lengths_from_source(
                    point, [tg for tg in self._points_to.geometry])

        # Fuel and travel time shortest path (loaded)
        for path, weight in zip([fuel_path, travel_time_path],
                                [self._weights["fuel_loaded"], self._weights["time_loaded"]]):
            self.network_model.network.build_graph(*weight)
            for n, point in enumerate(self._points_to.geometry):
                path["to_from"][:, n] = self.network_model.network.get_shortest_path_lengths_from_source(
                    point, [tg for tg in self._points_from.geometry])

        return travel_time_path, fuel_path

    def set_origin_and_destination(self, layer_from, layer_to):
        """ Set origin and destination points

        :param layer_from: geo layer
        :param layer_to: geo layer
        :return:
        """
        if self.configuration.use_centroid_projection:
            self._layer_from = layer_from.centroid()
            self._layer_to = layer_to.centroid()
        else:
            self._layer_from = layer_from
            self._layer_to = layer_to

        weights = \
            tuple([self.fuel_consumption[k1][k2] for k1 in self.fuel_consumption.keys() for k2 in
                   self.fuel_consumption[k1].keys()] + [self.travel_time[k1][k2] for k1 in self.travel_time.keys()
                                                        for k2 in self.travel_time[k1].keys()])
        self._points_from, self._points_to, *new_weights = \
            self.network_model.merge_layers_into_network(layer_from, layer_to, *weights)

        for n, key in enumerate(self._weights.keys()):
            self._weights[key] = [[npsum(w) for w in new_weights[2*n]], [npsum(w) for w in new_weights[2*n+1]]]


class RoadTransportationModel(TransportationModel):
    """ Class for modeling transport through road network

    """

    def __init__(self, configuration: RoadTransportationConfiguration):
        self.network_model_class = RoadNetworkModel
        super().__init__(configuration)

    @broadcast_event("Computing road segment fuel consumption", message_level=2)
    def _set_fuel_consumption(self):
        """ Set fuel consumption for road transportation

        :return:
        """
        for weight, key in zip([self.configuration.tare_weight, self.configuration.gross_weight], ["empty", "loaded"]):
            self.fuel_consumption[key] = \
                self.network_model.network.fuel_consumption(self.configuration.gross_hp, weight,
                                                            self.configuration.frontal_area,
                                                            self.configuration.engine_efficiency,
                                                            self.configuration.fuel_energy_density,
                                                            self.configuration.uphill_hp,
                                                            self.configuration.downhill_hp,
                                                            self.configuration.drag_resistance,
                                                            self.configuration.mass_correction_factor,
                                                            self.configuration.acceleration_rate,
                                                            self.configuration.deceleration_rate)

    @broadcast_event("Computing road segment travel time", message_level=2)
    def _set_travel_time(self):
        """ Set travel time for road transportation

        :return:
        """
        for weight, key in zip([self.configuration.tare_weight, self.configuration.gross_weight], ["empty", "loaded"]):
            self.travel_time[key] = self.network_model.network.travel_time(self.configuration.gross_hp, weight,
                                                                           self.configuration.acceleration_rate,
                                                                           self.configuration.deceleration_rate,
                                                                           self.configuration.uphill_hp,
                                                                           self.configuration.downhill_hp,
                                                                           self.configuration.time_format)


class BiomassGenerationModel(SpatialGenerationModel):
    pass


class BiomassModel(GeoModel):
    """ Implement the biomass resource/generation/transportation model

    The biomass model gathers resource, generation and transportation
    models into one interface
    """

    _transportation_model_class = dict(road=RoadTransportationModel, river=None, rail=None)

    generation_model = protected_property("generation_model")
    resource_model = protected_property("resource_model")
    transportation_model = protected_property("transportation_model")

    def __init__(self, configuration: BiomassConfiguration):
        """ Init BiomassModel class instance

        """
        super().__init__(configuration)

        # Set attribute fields
        self._generation_model = BiomassGenerationModel(configuration.biomass_generation)
        self._resource_model = BiomassResourceModel(configuration.biomass_resource)
        self._transportation_model = self._transportation_model_class[self.configuration.transport_type](
            configuration.biomass_transport)

    @broadcast_event("Computing shortest path", message_level=1)
    def get_shortest_path(self):
        """ Get shortest path between resource and generation polygons

        :return:
        """
        self._transportation_model.set_origin_and_destination(self._generation_model.polygons,
                                                              self._resource_model.polygons)
        path = self._transportation_model.get_shortest_path_length()

        for n in range(len(self._resource_model.polygons)):
            for p in path:
                self._generation_model.polygons["%s to resource %d" % (p["name"], n)] = p["from_to"].T[n]
                self._generation_model.polygons["%s from resource %d" % (p["name"], n)] = p["to_from"].T[n]

    def run(self):
        """ Run biomass model

        Run model, that is extract generation and resource polygons
        then compute shortest path between both
        :return:
        """
        # Extract polygons corresponding to power plants
        self._generation_model.extract_polygons()

        # Extract polygons corresponding to biomass resource
        self._resource_model.extract_polygons()

        # Get shortest path between polygons
        self.get_shortest_path()

        # Save results
        self.save_results()

    def save_results(self):
        """ Save results of model computation

        :return:
        """
        super().save_results()
        self._generation_model.save_results()
        self._resource_model.save_results()


class MixedGenerationModel(Model):
    """ Implement mix of renewable resource/generation

    """
    intersecting_matrix = None

    def __init__(self, configuration: MixedGenerationConfiguration):
        super().__init__(configuration)
        self.generation_1 = self.configuration.polygon_generation_1.to_crs(self.configuration.surface_crs)
        self.generation_2 = self.configuration.polygon_generation_2.to_crs(self.configuration.surface_crs)

    @broadcast_event("Compute intersecting matrix", message_level=1)
    def set_intersecting_matrix(self):
        self.intersecting_matrix = self.generation_1.intersecting_area(self.generation_2,
                                                                       self.configuration.is_normalized)

    def run(self, *args, **kwargs):

        self.set_intersecting_matrix()
        self.save_results()

    def save_results(self):
        super().save_results()
        df = DataFrame(data=self.intersecting_matrix,
                       index=["%s %d" % (self.generation_1.name, n + 1) for n in range(len(self.intersecting_matrix))],
                       columns=["%s %d" % (self.generation_2.name, n + 1) for n in range(len(
                           self.intersecting_matrix[0]))])
        df.to_csv(self.configuration.destination_path, float_format="%.2f")


# Network
class NetworkModel(GeoModel, metaclass=ABCMeta):
    """ Abstract class for implementing networks

    """

    network = None

    def __init__(self, configuration):
        super().__init__(configuration)
        self.edges = self.configuration.edge_layer.to_crs(self.configuration.crs)
        self.nodes = self.configuration.node_layer.to_crs(self.configuration.crs)
        self._init_network()

    # Abstract method to be overridden in sub-classes
    @abstractmethod
    def _init_network(self):
        """ Build network

        :return:
        """
        if self.configuration.find_disconnected_islands_and_fix:
            self.edges = find_all_disconnected_edges_and_fix(self.edges, self.configuration.find_and_fix_tolerance,
                                                             self.configuration.find_and_fix_method)

        if self.configuration.edge_resolution is not None:
            self.edges = self.edges.add_points_to_geometry(self.configuration.edge_resolution)

        if self.configuration.add_z_dimension:
            self.edges = self.edges.add_z(self.dem)

    def _project_onto_network(self, *layers):
        """ Project GeoLayer instance(s) on edges of network

        :param layers: collection of GeoLayer instances
        :return: collection of PointLayer instances corresponding to layers + location of nearest points in network
        """
        network_points = []
        for layer in layers:
            network_points.append(self.edges.nearest_point_in_layer(layer.project(self.edges)))

        outputs = [self.edges.get_underlying_points_as_new_layer(net) for net in network_points]
        outputs.append(sorted([loc for net in network_points for loc in net]))

        return tuple(outputs)

    @abstractmethod
    def _set_network(self):
        pass

    def merge_layers_into_network(self, layers_from, layers_to, *weights):
        """ Get shortest path from a list of polygons to another

        :param layers_from: GeoLayer instance
        :param layers_to: GeoLayer instance
        :return: points_from, points_to, new weights
        """

        points_from, points_to, network_pts = self._project_onto_network(layers_from, layers_to)
        result = [points_from, points_to]

        # New network
        self.edges, *new_weights = self.edges.split_at_underlying_points(network_pts, *weights)
        self.nodes = self.nodes.append(points_from.append(points_to))
        self._set_network()

        # Add new weights to result
        result.extend(new_weights)

        return result


class RoadNetworkModel(NetworkModel):
    """ Class for implementing road network

    """

    def _init_network(self):
        super()._init_network()
        self._set_network()

    def _set_network(self):
        self.network = RoadNetwork(self.edges, self.nodes, self.configuration.match_edge_nodes,
                                   self.configuration.node_tolerance)


class ElectricalNetworkModel(NetworkModel):
    """ Class for implementing electrical grid

    """

    def _init_network(self):
        super()._init_network()
        self._set_network()

    def _set_network(self):
        pass
        # self.network = ElectricalGrid(self.edges, self.nodes, self.configuration.match_edge_nodes,
        #                               self.configuration.node_tolerance)


class PVSystemModel(Model):
    """ Class for implementing PV model using pvlib library

    """
    # Inputs
    model_chain = None
    weather = None

    # Outputs
    dc_power = None
    ac_power = None

    @broadcast_event("Initializing PV model", message_level=1)
    def __init__(self, pv_configuration: PVSystemConfiguration):
        super().__init__(pv_configuration)

        # Init model chain and weather
        self._set_model_chain()
        self._set_weather()

    def _get_inverter_parameters(self):
        inverter = CEC_INVERTER_DATABASE[self.configuration.inverter_name]

        return inverter

    def _get_module_parameters(self):
        try:
            module = SANDIA_MODULE_DATABASE[self.configuration.module_name]
        except KeyError:
            module = CEC_MODULE_DATABASE[self.configuration.module_name]

        return module

    def _set_model_chain(self):
        """ Set pvlib model chain

        :return:
        """

        pv_systems = [PVSystem(tilt, azimuth, self.configuration.albedo,
                               module_parameters=self._get_module_parameters(),
                               modules_per_string=self.configuration.modules_per_string,
                               strings_per_inverter=self.configuration.strings_per_inverter,
                               inverter_parameters=self._get_inverter_parameters(),
                               racking_model=self.configuration.racking_model,
                               losses_parameters=self.configuration.losses_parameters) for tilt, azimuth in zip(
            self.configuration.surface_orientation["surface_tilt"], self.configuration.surface_orientation[
                "surface_azimuth"])]

        self.model_chain = [ModelChain(pv_system, location, clearsky_model=self.configuration.clear_sky_model,
                                       transposition_model=self.configuration.sky_diffuse_model,
                                       airmass_model=self.configuration.airmass_model,
                                       dc_model=self.configuration.dc_model, ac_model=self.configuration.ac_model,
                                       aoi_model=self.configuration.aoi_model,
                                       spectral_model=self.configuration.spectral_model,
                                       losses_model=self.configuration.losses_model) for pv_system, location in zip(
            pv_systems, self.configuration.location)]

    def _set_weather(self):
        self.weather = [DataFrame({'ghi': ghi, 'dni': dni, 'dhi': dhi, 'temp_air': temp, 'wind_speed': wind_spd}) for
                        ghi, dni, dhi, temp, wind_spd in zip(self.configuration.ghi, self.configuration.dni,
                                                             self.configuration.dhi, self.configuration.air_temperature,
                                                             self.configuration.wind_speed)]

    def get_array_nominal_power(self):
        """ Get nominal power of PV array

        :return:
        """
        try:
            module_nominal_power = CEC_MODULE_DATABASE[self.configuration.module_name]["STC"]
        except KeyError:
            module_nominal_power = SANDIA_MODULE_DATABASE[self.configuration.module_name]["Impo"] * \
                                   SANDIA_MODULE_DATABASE[self.configuration.module_name]["Vmpo"]

        return self.get_number_of_modules_in_array() * module_nominal_power

    def get_array_vmp(self):
        """ Get STC MPP voltage of PV array

        :return:
        """
        try:
            module_vmp = CEC_MODULE_DATABASE[self.configuration.module_name]["V_mp_ref"]
        except KeyError:
            module_vmp = SANDIA_MODULE_DATABASE[self.configuration.module_name]["Vmpo"]

        return self.configuration.modules_per_string * module_vmp

    def get_array_voc(self):
        """ Get STC voltage of PV array

        :return:
        """
        try:
            module_voc = CEC_MODULE_DATABASE[self.configuration.module_name]["V_oc_ref"]
        except KeyError:
            module_voc = SANDIA_MODULE_DATABASE[self.configuration.module_name]["Voco"]

        return self.configuration.modules_per_string * module_voc

    def get_inverter_max_vmp(self):
        return CEC_INVERTER_DATABASE[self.configuration.inverter_name]["Mppt_high"]

    def get_inverter_min_vmp(self):
        return CEC_INVERTER_DATABASE[self.configuration.inverter_name]["Mppt_low"]

    def get_inverter_nominal_power(self):
        return CEC_INVERTER_DATABASE[self.configuration.inverter_name]["Paco"]

    def get_land_usage(self):
        """ Get land area occupied by PV array

        :return:
        """

        return self.get_total_module_area() / self.configuration.ground_coverage_ratio

    def get_number_of_modules_in_array(self):
        """ Get number of modules in PV array

        :return:
        """

        return self.configuration.modules_per_string * self.configuration.strings_per_inverter

    def get_system_features(self):
        """ Get features of PV system

        :return:
        """
        features = DataFrame({'Name': ["Nominal power", "Number of modules", "Total module area", "Land usage",
                                       "Voltage", "MPP voltage", "Inverter MPP voltage range", "PV-to-inverter ratio"],
                              'Value': ["%.2f Wc" % self.get_array_nominal_power(),
                                        "%d" % self.get_number_of_modules_in_array(),
                                        "%.2f m2" % self.get_total_module_area(), "%.2f m2" % self.get_land_usage(),
                                        "%.2f Vdc" % self.get_array_voc(), "%.2f Vdc" % self.get_array_vmp(),
                                        "%.2f - %.2f Vdc" % (self.get_inverter_min_vmp(), self.get_inverter_max_vmp()),
                                        "%.2f" % (self.get_array_nominal_power() / self.get_inverter_nominal_power())]})

        return features

    def get_total_module_area(self):
        """ Get total area of PV array

        :return:
        """
        try:
            unit_area = CEC_MODULE_DATABASE[self.configuration.module_name]["A_c"]
        except KeyError:
            unit_area = SANDIA_MODULE_DATABASE[self.configuration.module_name]["Area"]

        return self.get_number_of_modules_in_array() * unit_area

    def run(self):
        self.run_model()
        self.save_results()

    @broadcast_event("Running model", message_level=1)
    def run_model(self):
        """ Run model

        :return:
        """
        # Initialize dc, ac energy and simulation time step
        dc_output = []
        ac_output = []
        time = date_range(self.weather[0].index[0].floor("H"), self.weather[0].index[-1].ceil("H"), freq="1H")

        # Run for each polygon
        for location, mc, weather in zip(self.configuration.location, self.model_chain, self.weather):
            mc.run_model(weather.index, weather)
            dc_output.append(irradiance_to_irradiation(mc.dc["p_mp"], time, location,
                                                       self.configuration.power_to_energy_method))
            ac_output.append(irradiance_to_irradiation(mc.ac, time, location,
                                                       self.configuration.power_to_energy_method))

        self.dc_power = DataFrame({"polygon %d" % (n + 1): dc for n, dc in enumerate(dc_output)})
        self.ac_power = DataFrame({"polygon %d" % (n + 1): ac for n, ac in enumerate(ac_output)})

    def save_results(self):
        """ Save results to csv files

        :return:
        """
        super().save_results()

        if self.configuration.destination_path["dc"] is not None:
            self.dc_power.to_csv(self.configuration.destination_path["dc"], float_format="%.2f", index=True)

        if self.configuration.destination_path["ac"] is not None:
            self.ac_power.to_csv(self.configuration.destination_path["ac"], float_format="%.2f", index=True)

        if self.configuration.destination_path["features"] is not None:
            self.get_system_features().to_csv(self.configuration.destination_path["features"], index=False)


# class MixedGenerationModel(metaclass=ABCMeta):
#     """ Implement mix of renewable resource/generation
#
#     """
#
#     def _apply_difference(self, model1, model2):
#         for m1, m2 in zip([model1, model2], [model2, model1]):
#             self._set_new_config(m1.configuration, m1.polygons, [m2.polygons, 0])
#
#     def _apply_intersection(self, model1, model2):
#         base_layer = model1.polygons.overlay(model2.polygons, "intersection")
#         for model in [model1, model2]:
#             self._set_new_config(model.configuration, base_layer, [])
#
#     @staticmethod
#     def _set_new_config(config, base_layer, list_of_mask_layers):
#         config.base_layer = base_layer.copy()
#         config.list_of_mask_layers = list_of_mask_layers
#
#
# class SolarBiomassModel(MixedGenerationModel):
#     """ Implement mix of solar PV and biomass
#
#     """
#
#     def __init__(self, solar_model, biomass_model):
#         """ Build model
#
#         :param solar_model: SolarGHIModel class instance
#         :param biomass_model: BiomassModel class instance
#         """
#         self.solar_model = solar_model
#         self.biomass_model = biomass_model
#
#     def _get_difference_polygons(self):
#         self._apply_difference(self.solar_model, self.biomass_model.generation_model)
#         return self._get_polygons()
#
#     def _get_intersection_polygons(self):
#         self._apply_intersection(self.solar_model, self.biomass_model.generation_model)
#         return self._get_polygons()
#
#     def _get_polygons(self):
#         self.solar_model.extract_polygons()
#         self.biomass_model.generation_model.extract_polygons()
#         self.biomass_model.get_shortest_path()
#
#         return self.solar_model.polygons.copy(), self.biomass_model.generation_model.polygons.copy()
#
#     def run(self):
#         """ Run model
#
#         :return:
#         """
#         self.solar_model.run()
#         self.biomass_model.run()
#
#         # Retrieve new mixed polygons
#         diff_polygons = self._get_difference_polygons()
#         intersect_polygons = self._get_intersection_polygons()
#
#         polygons = diff_polygons[0].append(diff_polygons[1])


if __name__ == "__main__":
    from greece.rentools.configuration import SolarGHIConfiguration
    config = SolarGHIConfiguration("/home/benjamin/ownCloud/Post-doc Guyane/GREECE model/Config files/"
                                   "Main configuration/main.config", "/home/benjamin/ownCloud/Post-doc Guyane/"
                                                                     "GREECE model/Config files/Solar GHI/solar.config")
    model = SolarGHIModel(config)
    model.run()
