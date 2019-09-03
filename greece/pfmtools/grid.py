# -*- coding: utf-8 -*-

""" Power grid configuration

Gathers all classes/methods related to power grid
structure.
"""
import re

import networkx as nx
from shapely.geometry import Point
from numpy import nan, full

from gistools.layer import PolygonLayer, intersecting_features
from gistools.network import Edge, Network, Node
from utils.check import protected_property, type_assert
from utils.sys.timer import Timer

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2019, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


def _longest_in_multi(multi, length):
    """ Get longest edges between 2 nodes

    Return IDs of longest edges between 2 nodes
    :param multi: output from 'get_multi_edges' method
    :param length: length of associated edges in graph
    :return: list of edge IDs
    """
    return [edge_id for n in multi for _, edge_id in sorted(zip(length[n][:-1], n[:-1]))]


class ElectricalNode(Node):

    def __init__(self, nodes, *args, **kwargs):
        super().__init__(nodes, *args, **kwargs)
        self._polygon_layer_class = Substation
        self._line_layer_class = PowerLine
        self._point_layer_class = ElectricalNode


class PowerLine(Edge):
    """ PowerLine class for power line in grid

    """

    def __init__(self, power_lines, voltage_key=None, *args, **kwargs):
        """ PowerLine class constructor

        :param power_lines:
        :param voltage_key: layer attribute name corresponding to voltage
        :param args:
        :param kwargs:
        """
        super().__init__(power_lines, *args, **kwargs)

        self._point_layer_class = ElectricalNode
        self._line_layer_class = PowerLine
        self.voltage_key = voltage_key

    def clean_topology(self):
        """ Simplify topology

        Simplify topology of power lines by merging
        edges and removing redundant ones
        :return:
        """
        new_lines = self.copy()

        # Remove redundant and merge edges as long as needed
        number_of_lines = len(new_lines)
        while "There are lines to merge/remove":
            new_lines = new_lines.remove_redundant()
            new_lines = new_lines.merge2()
            if len(new_lines) < number_of_lines:
                number_of_lines = len(new_lines)
            else:
                break

        return new_lines

    def remove_redundant(self):
        """ Remove redundant lines

        Remove redundant lines, that is multiple lines
        between the same nodes, self-loop lines, etc.
        :return:
        """
        return self.drop(self.get_self_loops() + _longest_in_multi(self.get_multi_edges(), self.length.to_numpy()))

    @property
    def voltage(self):
        if self.voltage_key is None:
            return full((len(self),), nan)
        else:
            # Accept voltage as digit or string, and replace comma by point
            return [float(re.search("[0-9.]+", str(voltage).replace(",", "."))[0])
                    if re.search("[0-9.]+", str(voltage)) else nan for voltage in self[self.voltage_key]]


class Substation(PolygonLayer):
    """ Substation class for substation in grid

    """
    voltage = PowerLine.voltage

    def __init__(self, substations, voltage_key=None, *args, **kwargs):
        super().__init__(substations, *args, **kwargs)
        self.voltage_key = voltage_key

        # Create one SubStation instance for each substation
        if "SubStation" not in self.attributes():
            self["SubStation"] = [self.SubStation(v) for v in self.voltage]

        # Override point layer class attribute
        self._polygon_layer_class = Substation
        self._line_layer_class = PowerLine
        self._point_layer_class = ElectricalNode

    def add_power_station(self, idx, power_station):
        """ Add power station to given substation in layer

        :param idx:
        :param power_station:
        :return:
        """
        self["SubStation"].iloc[idx].add_power_station(power_station)

    def to_file(self, file_path, driver="ESRI Shapefile", **kwargs):
        """ Override superclass method

        Override to ensure writing attribute table to file without
        SubStation class instances
        :param file_path:
        :param driver:
        :param kwargs:
        :return:
        """
        if "SubStation" in self.attributes():
            layer = self.copy()
            layer._gpd_df = layer._gpd_df.drop("SubStation", axis=1)
            layer.to_file(file_path, driver, **kwargs)
        else:
            super().to_file(file_path, driver, **kwargs)  # Use recursive form

    @property
    def substation(self):
        return self["SubStation"]

    class SubStation:
        """ Sub class for storing substation characteristics and connected power stations

        """
        def __init__(self, max_voltage):
            self.max_voltage = max_voltage
            self.power_stations = []

        def add_power_station(self, power_station):
            if power_station not in self.power_stations:
                self.power_stations.append(power_station)

        def __len__(self):
            return len(self.power_stations)


class PowerGrid(Network):
    """ PowerGrid class

    Use this class to implement electrical grid
    configuration from a set of geographic layers.

    Typically, a power grid is defined by a set of:
        - electrical lines
        - buses
        - transformers
        - loads
        - generators
    """

    substations = protected_property("substations")
    # lines = protected_property("edges")
    # loads = None
    _graph_nodes = None

    @type_assert(lines=PowerLine, substations=Substation)
    def __init__(self, lines, substations, buffer_substation=2):
        """ Build PowerGrid class instance

        :param lines: PowerLine class instance
        :param substations: Substation class instance
        :param buffer_substation: buffer value around substations
        """
        self._substations = substations
        self._buffer_substations = self.substations.buffer(buffer_substation)
        self._centroid_substations = self.substations.centroid()
        self.lines = lines

        super().__init__(self.lines, self.nodes, match_edge_nodes=False)

    def _update_nodes(self):
        """ Update nodes of power grid graph (lines junction + substations)

        """
        nodes = self.lines.get_nodes()
        self._graph_nodes = {(node.x, node.y): (node.x, node.y) for node in nodes.geometry}
        for substation, centroid in zip(self._buffer_substations.geometry, self._centroid_substations.geometry):
            _, within_nodes = intersecting_features(substation, nodes.geometry, nodes.r_tree_idx)
            self._graph_nodes.update({(node.x, node.y): (centroid.x, centroid.y) for node in within_nodes})

    def update(self):
        """ Update power grid

        :return:
        """
        self._edges = self._edges.clean_topology()
        self._update_nodes()
        self.build_graph()
        self._nodes = Node.from_gpd(geometry=[Point(val) for _, val in self._graph_nodes.items()],
                                    crs=self.substations.crs)

    def build_graph(self):
        """ Build corresponding graph

        Power grid graph is made of lines (edges) and substations/buses (nodes)
        :return:
        """
        self._graph = nx.MultiGraph()
        self._graph.add_edges_from([(self._graph_nodes[from_n], self._graph_nodes[to_n], _id,
                                     {'weight': w, 'voltage': v}) for _id, (from_n, to_n, w, v)
                                    in enumerate(zip(self.lines.from_node,
                                                     self.lines.to_node,
                                                     self.lines.length,
                                                     self.lines.voltage))])

    def clean_topology(self, reconnection):
        """ Clean topology of network before further abstraction

        :param reconnection: distance for considering lines as disconnected
        :return:
        """
        # Reconnect disconnected lines and remove lines within substations
        # Do not clean topology of lines after reconnection otherwise the merge can lead to issues... Instead,
        # directly overlay substation polygons and then let the lines being updated.
        self.lines = self.lines.reconnect(reconnection).overlay(self.substations, how="difference")

        # Remove redundant lines
        redundant_lines = self.get_self_loops() + self.get_remote_edges() + \
            _longest_in_multi(self.get_multi_edges(), self.lines.length.to_numpy())
        self.drop_lines(redundant_lines)

    def drop_lines(self, line_id):
        """ Drop power line by idx

        :param line_id: list of line IDs
        :return:
        """
        if line_id:
            self.lines = self.lines.drop(line_id)

    def plot(self, edge_color="blue", node_color="red", substation_color="green"):
        """ Override superclass method

        :param edge_color:
        :param node_color:
        :param substation_color:
        :return:
        """
        self.substations.plot(layer_color=substation_color)
        super().plot(edge_color, node_color)

    @property
    def lines(self):
        return self._edges

    @lines.setter
    def lines(self, lines):
        self._edges = lines
        self.update()


def build_power_grid(lines, substations, buffer=2, reconnection=30, crs=None):
    """ Build power grid abstraction

    :param lines:
    :param substations:
    :param buffer: buffer around substations (in m)
    :param reconnection: tolerance for reconnecting lines (in m)
    :param crs: coordinate reference system to use for distance calculations
    :return:
    """

    if crs is None:
        crs = lines.crs

    lines = lines.clean_topology().to_crs(crs)
    substations = substations.to_crs(crs)
    power_grid = PowerGrid(lines, substations, buffer)
    power_grid.clean_topology(reconnection)

    return power_grid


if __name__ == "__main__":
    import os
    from greece import data_dir
    overhead_lines = PowerLine("/home/benjamin/Desktop/Geo data/Power Grid/RTE/lignes-aeriennes-rte.geojson")
    underground_lines = PowerLine("/home/benjamin/Desktop/Geo data/Power Grid/RTE/lignes-souterraines-rte.geojson")
    with Timer() as t:
        france_pwlines = overhead_lines.append(underground_lines)
    print("append time: %s" % t)
    with Timer() as t:
        france_pwlines = france_pwlines.clean_topology()
    print("clean topology time: %s" % t)
    france_pwlines.to_file(os.path.join(data_dir, "france_rte", "france_pwlines"))
    # from matplotlib import pyplot as plt
    # lines_ = PowerLine("/home/benjamin/Desktop/Power Grid/Lignes "
    #                    "électriques/electrical_lines_gard.shp", "tension")
    # postes_transfo = Substation("/home/benjamin/Desktop/Power Grid/Lignes "
    #                             "électriques/postes_transfo_gard.shp")
    # power_grid = build_power_grid(lines_, postes_transfo, crs={'init': 'epsg:2154'})
    # nx.draw(power_grid.graph)
    # plt.show()
    # lines_ = lines_.reconnect(30)
    # lines_.to_file("/home/benjamin/Desktop/Power Grid/Lignes électriques/electrical_lines_gard_merge.shp")
    # print("spent time: %s" % t)
    # lines_.to_file("/home/benjamin/Desktop/Power Grid/Lignes électriques/electrical_lines_gard_test.shp")
    # grid = PowerGrid(lines_, postes_transfo)
    # with Timer() as t:
    #     grid.clean_network_topology(reconnection_tolerance=30)
    # print("spent time: %s" % t)
    # test = test.to_crs(epsg=4326)
    # new_lines = grid.lines.to_crs(epsg=4326)
    # test = grid.lines.get_single_edges()
    # print(len(test))
    # lines_.to_file("/home/benjamin/Desktop/Power Grid/Lignes électriques/electrical_lines_gard_merge.shp")
