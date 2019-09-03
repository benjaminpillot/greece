# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""
import matplotlib.pylab as plt
import pandas as pd

from matplotlib import dates as mdates

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2019, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


def pandas_plot(data_frame, year=2030, loop=True, fontsize=18, month_interval=None, day_interval=None):
    """

    :param data_frame:
    :param year:
    :param loop: add first value to the end
    :param fontsize:
    :param month_interval:
    :param day_interval:
    :return:
    """
    data_frame.index = pd.DatetimeIndex(data_frame.index)
    if loop:
        df = data_frame.iloc[[0]]
        df.index = df.index + pd.DateOffset(years=1)
        data_frame = data_frame.append(df)

    data_frame.index += pd.DateOffset(years=year-data_frame.index[0].year)
    data_frame.index = [pd.to_datetime(date, format='%Y-%m-%d %H:%M') for date in data_frame.index]

    ax = data_frame.plot(fontsize=fontsize)
    if month_interval:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=month_interval))
    elif day_interval:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=day_interval))

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.set_xlim(left=data_frame.index[0].date(), right=data_frame.index[-1].date())
    plt.gcf().autofmt_xdate()

    return ax


if __name__ == "__main__":
    df = pd.read_csv("/home/benjamin/Documents/Data/Impact-35-WORST SCENARIO.csv", index_col=0, sep=",")
    df = df[["Total PV with 35", "Total PV without 35"]]
    df["constraint"] = 35
    df1 = df[["Total PV without 35", "constraint"]]
    fontsize = 24
    ax = pandas_plot(df1, fontsize=fontsize)
    ax.set_ylabel("Power penetration (%)", fontsize=fontsize)
    ax.set_ylim(0, 60)
    ax.legend(["PV power", "35% constraint"], fontsize=fontsize)
    plt.show()

    df2 = df[["Total PV with 35", "constraint"]]
    ax = pandas_plot(df2, fontsize=fontsize)
    ax.set_ylabel("Power penetration (%)", fontsize=fontsize)
    ax.set_ylim(0, 60)
    plt.show()

    df = pd.read_csv("/home/benjamin/Desktop/Article Applied figures/Power demand/POWERDEMANDFG.csv", index_col=1,
                     sep=";")
    df = df[["EDMIN(MW)2030", "EDMAX(MW)2030"]]
    ax = pandas_plot(df, fontsize=fontsize)
    ax.set_ylabel("Power (MW)", fontsize=fontsize)
    ax.set_ylim(80, 240)
    ax.legend(["Forecast minimum power demand", "Forecast maximum power demand"], fontsize=fontsize)
    plt.show()
