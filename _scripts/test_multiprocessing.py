# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

import multiprocessing as mp
import numpy as np
from utils.sys.timer import Timer

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2019, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


def sum_of_cubes(args):
    return sum(x**3 + args[1] for x in args[0])


def howmany_within_range(row, minimum, maximum):
    """Returns how many numbers lie within `maximum` and `minimum` in a given `row`"""
    count = 0
    for n in row:
        if minimum <= n <= maximum:
            count = count + 1
    return count


def func_test(p):
    d = []
    for x in p:
        d.append(x)
    return d


def mp_test():
    pool = mp.Pool(6)
    test = [pool.apply(func_test, args=(var,)) for var in [(2, 1, 4, 1, 5), (8, 9, 7, 6)]]
    pool.close()
    return test


l = mp_test()

count = 10
value = np.random.random(10000).tolist()

# Step 1: Init multiprocessing.Pool()
pool = mp.Pool(10)

with Timer() as t:
    for n in count * [value]:
        results = sum_of_cubes([n, 5])

print("spent time without parallelization: %s" % t)

with Timer() as t:
    # Step 2: `pool.apply` the `howmany_within_range()`
    # results = [pool.apply(sum_of_cubes, args=(val,)) for val in count * [value]]
    results = pool.map(sum_of_cubes, [count * [value, 5]])

print("spent time with parallelization: %s" % t)

print(results)

# Step 3: Don't forget to close
pool.close()
