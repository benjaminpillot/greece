# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""
from setuptools import setup, find_packages

import greece

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2019, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


with open("README.md", 'r') as fh:
    long_description = fh.read()

setup(name='greece',
      version=greece.__version__,
      description='GREECE model',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='http://github.com/benjamin2b/greece',
      author='Benjamin Pillot',
      author_email='benjaminpillot@riseup.net',
      install_requires=["python-dateutil>=2.7.5",
                        "elevation>=1.0.5",
                        "gis-tools>=0.15.7",
                        "greece-utils>=0.1.0",
                        "matplotlib>=2.2.3",
                        "networkx>=2.1",
                        "numpy>=1.14.3",
                        "pandas>=0.23.4",
                        "pvlib>=0.6.0",
                        "pytz>=2018.7",
                        "rtree>=0.8.3",
                        "scipy>=1.1.0",
                        "shapely>=1.6.4"
                        "tables>=3.4.4"],
      license='GNU GPL v3.0',
      packages=find_packages(),
      zip_safe=False)
