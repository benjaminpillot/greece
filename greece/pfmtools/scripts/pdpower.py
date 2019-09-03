# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

__version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


from pandapower.plotting.plotly import simple_plotly
from pandapower.networks import mv_oberrhein
from pandapower import runpp
net = mv_oberrhein()
runpp(net)
simple_plotly(net)
