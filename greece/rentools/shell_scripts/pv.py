#!/usr/bin/env python3

""" Module summary description.

More detailed description.
"""

from greece.rentools.configuration import PVSystemConfiguration
from greece.rentools.model import PVSystemModel
from greece.rentools.shell_scripts import run_model

__version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


description = 'Simulate a solar PV system and save AC/DC output power to file using model config file located in ' \
              'directory specified by the user'

run_model(PVSystemConfiguration, PVSystemModel, description, "pv_model", "main.config", "pv_model.config")
