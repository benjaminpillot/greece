#!/usr/bin/env python3

""" Module summary description.

More detailed description.
"""
from greece.rentools.configuration import MixedGenerationConfiguration
from greece.rentools.model import MixedGenerationModel
from greece.rentools.shell_scripts import run_model

__version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


def main():
    description = 'Model mixed renewable generation and save corresponding results such as intersecting matrix'

    run_model(MixedGenerationConfiguration, MixedGenerationModel, description, "mixed_generation", "main.config",
              "mixed_generation.config")


if __name__ == "__main__":
    main()


