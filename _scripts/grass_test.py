# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

from grass_session import Session
from grass.script import core as gcore

# __all__ = []
# __version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


with Session(gisdb="/tmp", location="location", create_opts="EPSG:4326"):
    print(gcore.parse_command("g.gisenv", flags="s"))


if __name__ == "__main__":
    pass