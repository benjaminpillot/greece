# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'
import os
import tempfile

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


import logging
import sys


class StreamToLogger:
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """
    def __init__(self, logger, name="out", log_level=logging.ERROR):
        self.path = os.path.join(tempfile.gettempdir(), name + ".log")
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''
        logging.basicConfig(level=self.log_level,
                            format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
                            filename=self.path,
                            filemode='a')

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())


# stdout_logger = logging.getLogger('STDOUT')
# sl = StreamToLogger(stdout_logger, logging.INFO)
# sys.stdout = sl

stderr_logger = logging.getLogger('STDERR')
sys.stderr = StreamToLogger(stderr_logger, log_level=logging.ERROR)

print("Test to standard out")
raise Exception('Test to standard error')
