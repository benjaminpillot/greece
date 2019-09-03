# -*- coding: utf-8 -*-

""" Time series methods and classes

More detailed description.
"""
from numpy import interp
from pandas import Series, DatetimeIndex
from functools import wraps
from collections.abc import Collection

from utils.check import check_type, check_type_in_collection

# __all__ = ["TimeSeries"]
# __version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2017, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


# Decorator for returning new instance of TimeSeries and subclasses
def return_new_instance(method):
    @wraps(method)
    def _return_new_instance(self, *args, **kwargs):
        series = method(self, *args, **kwargs)
        if isinstance(series, Series):
            new_self = self.__class__(series)
            return new_self
        else:
            return series
    return _return_new_instance


class TimeSeriesError(Exception):
    pass


class TimeSeries(Series):
    """ TimeSeries base class

    Use this class as a generic for any time series
    related computations
    """
    def __init__(self, time, data=None, dtype=None):
        """ TimeSeries constructor

        Build time series from data and time.

        :param data: data collection
        :type data: list, tuple, set, array, etc. collection of data
        :param time: time collection. Must be convertible into DatetimeIndex
        :type time: collection of datetime (string, datetime object, DatetimeIndex, etc.)
        :param dtype: data dtype (if None, dtype is inferred)
        :type dtype: str or None (valid numpy dtype)

        :Example:
            * Create full time series
            >>> tms = TimeSeries(["22-dec-2006 10:00", "22-dec-2006 11:00"], [2,3])
            * Create time series with merely index
            >>> tms = TimeSeries(["22-sep-2006 11:00", "23-sep-2006 12:00"])
        """

        if not isinstance(time, (Series, TimeSeries)):

            # Check time is a collection and avoid unwilling int and float elements
            check_type(time, Collection)
            check_type_in_collection(time, (int, float), include=False)

            # Check if time collection is valid (DatetimeIndex should work)
            try:
                time = DatetimeIndex(time)
            except (ValueError, TypeError) as e:
                raise TimeSeriesError("Invalid time format: {}".format(e))
            except Exception as e:
                raise TimeSeriesError("Unexpected error when parsing time input: {}".format(e))

            try:
                super().__init__(data, index=time, dtype=dtype)
            except(ValueError, TypeError) as e:
                raise TimeSeriesError("Invalid data format: {}".format(e))
            except Exception as e:
                raise TimeSeriesError("Unexpected error when parsing data: {}".format(e))

        else:
            super().__init__(time)

    @property
    def time(self):
        return self.index

    @return_new_instance
    def __getitem__(self, item):
        return super().__getitem__(item)

    @return_new_instance
    def __mul__(self, other):
        return super().__mul__(other)

    @return_new_instance
    def sort_index(self, *args, **kwargs):
        return super().sort_index(*args, **kwargs)


def interp_time_series(series, time=None, other=None):
    """ Interpolate time series values on index of other

    :param series: pandas Series
    :param time: pandas DatetimeIndex or equivalent
    :param other: pandas Series
    :return:
    """
    series_julian_time = Series(series.index.to_julian_date(), series.index)
    if other is None:
        try:
            time = DatetimeIndex(time)
            other_julian_time = Series(time.to_julian_date(), time)
        except ValueError:
            raise TypeError("'time' must either be or convertible into a DatetimeIndex")
        except AttributeError:
            raise ValueError("Either 'other' or 'time' must be passed")
    else:
        other_julian_time = Series(other.index.to_julian_date(), other.index)
        time = other.index

    # Interpolate values
    value_interp = interp(other_julian_time.values, series_julian_time.values, series.values)

    return Series(data=value_interp, index=time)
