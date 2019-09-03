# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2019, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


# def _remove_redundant_lines_in_network(self):
#     """ Remove redundant lines in network (only lines intersecting with lines)
#
#     :return:
#     """
#     while "There are lines to drop":
#
#         leave_loop = True
#         redundant_lines = []
#
#         for id_line, line in enumerate(self._edges.geometry):
#             _, intersecting_lines = intersecting_features(line, self._edges.geometry, self._edges.r_tree_idx)
#             _, substations = intersecting_features(line, self.buff_substations.geometry,
#                                                    self.buff_substations.r_tree_idx)
#             other_lines = [other_line for other_line in intersecting_lines if other_line is not line]
#             drop = False
#
#             # TEST
#             if is_double_connected(line, substations):
#                 # Test if double connected to the same substation
#                 drop = True
#             # elif is_one_connected(line, other_lines) and not substations:
#             # Test if connected to line on one end and to nothing on the other
#             # drop = True
#             # elif is_one_connected(line, substations) and not is_connected(line, other_lines):
#             # Test if connected to substation on one end and to nothing on the other
#             # drop = True
#             elif not substations:
#                 # Test if line is "alone" (i.e. connected from nothing to nothing)
#                 if not other_lines:
#                     drop = True
#                 else:
#                     if not is_connected(line, other_lines):
#                         drop = True
#
#             # Drop line from Rtree index if necessary
#             if drop:
#                 self._edges.r_tree_idx.delete(id_line, line.bounds)
#                 redundant_lines.append(id_line)
#                 leave_loop = False
#
#         if leave_loop:
#             break
#
#         self._edges = self._edges.drop(redundant_lines)
#
#     return self
#
#
# def _remove_redundant_lines_to_substations(self):
#     """ Remove "fork" artifact: when a line is split in 2 near a substation/generator
#
#     :return:
#     """
#     redundant_lines = []
#
#     for substation in self.buff_substations.geometry:
#         # Find lines intersecting with substation
#         id_lines, lines = intersecting_features(substation, self._edges.geometry, self._edges.r_tree_idx)
#         for id_line, line in zip(id_lines, lines):
#             other_lines = [geom for geom in lines if geom is not line]
#             if is_connected(line, other_lines):
#                 redundant_lines.append(id_line)
#                 self._edges.r_tree_idx.delete(id_line, line.bounds)
#
#     self._edges = self._edges.drop(redundant_lines)
#
#     return self

# def any_intersect(geometry, geometry_collection, idx):
#     """
#
#     :param geometry:
#     :param geometry_collection:
#     :param idx: rtree index
#     :return:
#     """
#     return any(intersects(geometry, geometry_collection, idx))
#
#
# def is_connected(aline, geometry_collection):
#     """ Test if line is connected to any geometries in collection
#
#     :param aline:
#     :param geometry_collection:
#     :return:
#     """
#     start, end = is_line_connected_to(aline, geometry_collection)
#     return any([any(start), any(end)])
#
#
# def is_double_connected(aline, geometry_collection):
#     """ Is line double connected to the same geometry in collection ?
#
#     :param aline:
#     :param geometry_collection:
#     :return:
#     """
#     start, end = is_line_connected_to(aline, geometry_collection)
#     return True if [i for i, (x, y) in enumerate(zip(start, end)) if x and y] else False
#
#
# def is_one_connected(aline, geometry_collection):
#     """ Test is line is only connected by one end
#
#     :param aline:
#     :param geometry_collection:
#     :return:
#     """
#     start, end = is_line_connected_to(aline, geometry_collection)
#     return any(start) ^ any(end)  # XOR

# def pandas_to_layer(data_frame, layer, on, merge=True):
#     """ Build geo layer with pandas data frame attributes
#
#     Merge pandas data frame with layer geometry based on a shared attribute
#     :param data_frame:
#     :param layer:
#     :param on: attribute shared by both data frame and layer and used for merging
#     :param merge: if True, merge attributes from both tables
#     :return:
#     """
#     if on not in layer.attributes() or on not in data_frame.columns:
#         raise ValueError("Attribute must be shared by both data frame and layer")
#
#     # Keep only data shared by both tables in "on" attribute
#     data_frame = data_frame[data_frame[on].isin(layer[on])]
#     geo_data_frame = layer._gpd_df[layer[on].isin(data_frame[on])]
#
#     # Initialize
#     df = [data_frame[data_frame[on] == val] for val in geo_data_frame[on]]
#     pd_df = concat(df, ignore_index=True)
#     gpd_df = DataFrame(repeat(geo_data_frame.values, [len(d) for d in df], axis=0), columns=geo_data_frame.columns)
#
#     merge_df = concat([pd_df, gpd_df], axis=1)
#
#     return layer.from_gpd(merge_df, crs=layer.crs)
#
#     # TODO: add the possibility of multiple shared attributes
