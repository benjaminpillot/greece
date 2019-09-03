# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'
from functools import wraps
from time import sleep

from utils.sys.timer import progress, broadcast_event, display_progress

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


class A:

    @broadcast_event("Testing through class")
    def long_running_function(self):
        sleep(4)

    @broadcast_event("Computing")
    def other_long_running_function(self):
        sleep(4)


if __name__ == "__main__":
    display_progress()
    x = A()
    x.long_running_function()
    x.other_long_running_function()
    x.long_running_function()
