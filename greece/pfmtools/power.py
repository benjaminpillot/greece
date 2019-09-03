# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2019, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


class PowerStation:
    """ Power station class definition

    Define attributes of power station (power, voltage, etc.)
    """

    def __init__(self, power, voltage, name=None):
        self.power = power
        self.voltage = voltage
        self.name = name


class Storage(PowerStation):
    pass


class NuclearPowerStation(PowerStation):
    pass


class HydroPowerStation(PowerStation):
    pass


class TidalPowerStation(PowerStation):
    pass


class WindPowerStation(PowerStation):
    pass


class SolarPowerStation(PowerStation):
    pass


class ThermalPowerStation(PowerStation):
    pass


class BioPowerStation(PowerStation):
    pass


class GeothermalPowerStation(PowerStation):
    pass
