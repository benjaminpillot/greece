# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'
import os
from importlib import reload

from pvlib import spa

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2017, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


# By default, use numba when computing solar positions (see pvlib)
os.environ["PVLIB_USE_NUMBA"] = '1'
reload(spa)
