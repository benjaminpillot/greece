import networkx as nx
import metis
import numpy as np
import nxmetis
from matplotlib import pyplot as plt
from shapely.ops import cascaded_union

from gistools.geometry import katana_centroid, polygon_collection_to_graph, explode
from gistools.layer import PolygonLayer
from geopandas import GeoDataFrame

graph = nx.Graph()
graph.add_edges_from([(n, n+1) for n in range(50)])
for n in graph.nodes:
    graph.add_node(n, weight1=[n, n], weight2=len(graph.nodes) - n)

nparts = 10
tpweights = [[1/nparts, 1/nparts] for _ in range(nparts)]
_, partition = nxmetis.partition(graph, nparts, node_weight="weight1", tpwgts=tpweights, recursive=False,
                                 options=nxmetis.MetisOptions(iptype=3, rtype=1, contig=True, ncuts=10))

print(partition)
