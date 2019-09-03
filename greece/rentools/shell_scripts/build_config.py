#!/usr/bin/env python3

""" Script for building config file

More detailed description.
"""
import argparse
import os
import shutil

from greece.rentools import _path_to_config as src


__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2019, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


def parse_config_dir():
    parser = argparse.ArgumentParser(description="Build config files in specified directory")
    parser.add_argument('-t', '--type', required=True, choices=['solar', 'biomass', 'pv'],
                        help="Enter type of config file to build {'solar', 'biomass', 'pv'}")
    parser.add_argument('directory', metavar='dir', type=str, default=os.getcwd(),
                        help="Directory where config file(s) will be built")

    args = parser.parse_args()

    return args.directory, args.type


def build_files(directory, ctype):

    try:
        greece_dir = os.path.join(directory, "greece_%s_config" % ctype)
        os.mkdir(greece_dir)
    except FileNotFoundError:
        raise ValueError("'%s' is not a valid directory" % directory)

    if ctype == "solar":
        shutil.copy(os.path.join(src, 'solar/solar.config'), os.path.join(greece_dir, 'solar.config'))
        shutil.copy(os.path.join(src, 'solar/solar_mask.csv'), os.path.join(greece_dir, 'mask.csv'))
        shutil.copy(os.path.join(src, 'solar/solar_distance_threshold.csv'), os.path.join(greece_dir,
                                                                                          'distance_threshold.csv'))
        shutil.copy(os.path.join(src, 'solar/solar_distance_from_poly_to_layer.csv'),
                    os.path.join(greece_dir, 'distance_from_poly_to_layer.csv'))

    elif ctype == "pv":
        shutil.copy(os.path.join(src, 'energy system models/pv.config'), os.path.join(greece_dir, 'pv.config'))

    # Copy main config
    shutil.copy(os.path.join(src, 'main/main.config'), os.path.join(greece_dir, 'main.config'))


def main():
    build_files(*parse_config_dir())


if __name__ == "__main__":
    main()
