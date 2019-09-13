#!/usr/bin/env python3

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'

from greece.rentools.configuration import BiomassConfiguration
from greece.rentools.model import BiomassModel
from greece.rentools.shell_scripts import run_model

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


description = 'Compute biomass resource/generation polygons and save it to geo/table file(s) using given config ' \
              'files located in directory specified by the user'

run_model(BiomassConfiguration, BiomassModel, description, "biomass", "main.config", "biomass.config")
