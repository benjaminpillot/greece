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


import pygmsh
import numpy as np

geom = pygmsh.built_in.Geometry()

# Draw a cross.
poly = geom.add_polygon([
    [0.0,  0.5, 0.0],
    [-0.1,  0.1, 0.0],
    [-0.5,  0.0, 0.0],
    [-0.1, -0.1, 0.0],
    [0.0, -0.5, 0.0],
    [0.1, -0.1, 0.0],
    [0.5,  0.0, 0.0],
    [0.1,  0.1, 0.0]
    ],
    lcar=0.05
    )

axis = [0, 0, 1]

geom.extrude(poly, translation_axis=axis, rotation_axis=axis, point_on_axis=[0, 0, 0], angle=2.0 / 6.0 * np.pi)

points, cells, point_data, cell_data, field_data = pygmsh.generate_mesh(geom)


if __name__ == "__main__":
    pass
