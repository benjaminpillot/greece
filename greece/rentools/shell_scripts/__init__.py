# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""
import argparse
import logging
import os
import sys
from functools import wraps
from utils.sys.browser import find_file
from utils.sys.io import StreamToLogger
from utils.sys.timer import display_progress, Timer, broadcast_event

__version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


# Decorator
def execute_script(log_name="model_log"):
    def decorate(script):
        logging_name = log_name

        @wraps(script)
        def _execute_script(*args, **kwargs):

            # Log file
            # log = StreamToLogger(logging.getLogger('STDOUT'), name=logging_name, log_level=logging.INFO)
            # sys.stdout = log
            log = StreamToLogger(logging.getLogger('STDERR'), name=logging_name, log_level=logging.ERROR)
            sys.stderr = log

            # Display progress
            display_progress()

            # Execute
            try:
                with Timer() as computing_time:
                    script(*args, **kwargs)
            except Exception as e:
                print("\nJob stopped. Some error occurred. See log file '%s' for details" % log.path)
                raise RuntimeError("SubModel stopped because of:\n %s" % e)
            else:
                # Print everything's ok
                print("\nJob successfully completed in %s" % computing_time)
                print("See log file '%s' for further details" % log.path)

        return _execute_script

    return decorate


def parse_config_directory(description=None):
    """

    :param description:
    :return:
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('directory', metavar='dir', type=str, default=os.getcwd(),
                        help='directory where configuration file(s) are located')

    config_dir_path = parser.parse_args().directory

    return config_dir_path


def run_model(config_class, model_class, script_description, log_name, *config_file_name):

    @broadcast_event("Import configuration", message_level=1)
    def configuration():
        return config_class(*config_files)

    @execute_script(log_name)
    def execute_model():
        model = model_class(configuration())
        model.run()

    config_dir_path = parse_config_directory(description=script_description)

    # Create configuration
    config_files = []
    for file_name in config_file_name:
        try:
            config_files.append(find_file(file_name, config_dir_path)[0])
        except (IndexError, ValueError):
            raise RuntimeError("Unable to locate configuration file '%s' in directory '%s'" % config_dir_path)

    # Execute model
    execute_model()
