#! /home/benjamin/anaconda3/envs/benjamin/bin/python

""" Module summary description.

More detailed description.
"""

# import

# __all__ = []
# __version__ = '0.1'
import argparse
import numpy as np

# __author__ = 'Benjamin Pillot'
# __copyright__ = 'Copyright 2018, Benjamin Pillot'
# __email__ = 'benjaminpillot@riseup.net'


def main():
    parser = argparse.ArgumentParser(description='This is a demo script')
    parser.add_argument('integers', metavar='N', type=int, help='an integer for the sum', nargs='+')

    args = parser.parse_args()

    print(np.sum(args.integers))


if __name__ == "__main__":
    main()
