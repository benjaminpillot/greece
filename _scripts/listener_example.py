# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

import progressbar as pb
import time

# __all__ = []
# __version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


# Small implementation of the "observer pattern"
# (see https://en.wikipedia.org/wiki/Observer_pattern)
# Used in the SubModel-View-Controller pattern, an event
#  triggered by an object updates dependencies, here
# "Process" updates "ProgressBar"

class Process:
    def __init__(self):
        self._max_value = None
        self._update_value = 0
        self._observers = {"update": [], "max": []}

    @property
    def update_value(self):
        return self._update_value

    @property
    def max_value(self):
        return self._max_value

    @update_value.setter
    def update_value(self, value):
        self._update_value = value
        for callback in self._observers["update"]:
            callback(self._update_value)

    @max_value.setter
    def max_value(self, value):
        self._max_value = value
        for callback in self._observers["max"]:
            callback(self._max_value)

    def bind_to(self, callback):
        self._observers["update"].append(callback["update"])
        self._observers["max"].append(callback["max"])

    def run_process(self):
        for i in self.get_end_of_process(range(1000)):
            time.sleep(0.1)
            self.update_value += 1

    def get_end_of_process(self, iterator):
        self.max_value = len(iterator)
        return iterator


class Progress:
    def __init__(self, process):
        self.step = 0
        self.process = process
        self.process.bind_to({"update": self.update})

    def update(self):
        self.step += 1


if __name__ == '__main__':
    process = Process()
    progress = ProgressBar(process)
    process.run_process()
