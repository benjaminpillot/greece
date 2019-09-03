# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# import

# __all__ = []
# __version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


def apply_function(dictionary, func):

    for key in dictionary.keys():
        dictionary[key] = func(dictionary[key])

    return dictionary


def func_test(x):
    return x * 50


class Song:
    num = 0

    def __init__(self):
        self.__class__.num += 1

    def __del__(self):
        self.__class__.num -= 1


if __name__ == "__main__":
    dic = {"var1": 100, "var2": 200}
    result = apply_function(dic, func_test)
    print(result)
