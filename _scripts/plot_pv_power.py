# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""
import pandas as pd
from matplotlib import pyplot as plt

from _scripts.plot_pandas_series import pandas_plot

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2019, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'

ratio = 1/(1000 * 6.00372)
fontsize = 24
df = pd.read_csv("/home/benjamin/ownCloud/Post-doc Guyane/GREECE model/Results/Solar PV/"
                 "output_ac_power_permissive_contour.csv", index_col=0, sep=",")

# new_df = pd.DataFrame(index=df.index, columns=["C10", "C20", "C30", "C35", "C40", "C45", "C50", "C55", "C60", "C65"])
new_df = pd.DataFrame(index=df.index)
# new_df["P4, C65"] = df["polygon 6"] * 29.34 * ratio
new_df["P4, C65"] = df["polygon 6"] * ratio * 100
# new_df["P4, C45"] = df["polygon 6"] * 28.04 * ratio
# new_df["P3, C40"] = df["polygon 2"] * 24.78 * ratio
new_df["P3, C40"] = df["polygon 2"] * ratio * 100
# new_df["P2, C30"] = df["polygon 5"] * 17.29 * ratio
new_df["P2, C30"] = df["polygon 5"] * ratio * 100
# new_df["P1, C10"] = df["polygon 71"] * 4.66 * ratio
new_df["P1, C10"] = df["polygon 71"] * ratio * 100
# new_df["C20"] = df["polygon 5"] * 9.76 * ratio
# new_df["C30"] = df["polygon 5"] * 17.29 * ratio
# new_df["C35"] = df["polygon 2"] * 20.96 * ratio
# new_df["C40"] = df["polygon 2"] * 24.78 * ratio
# new_df["C45"] = df["polygon 6"] * 28.04 * ratio
# new_df["C50"] = df["polygon 6"] * 29.34 * ratio + df["polygon 71"] * 1.16 * ratio
# new_df["C55"] = df["polygon 6"] * 29.34 * ratio + df["polygon 71"] * 3.77 * ratio
# new_df["C60"] = df["polygon 5"] * 6.26 * ratio + df["polygon 6"] * 29.34 * ratio
# new_df["C65"] = df["polygon 5"] * 8.87 * ratio + df["polygon 6"] * 29.34 * ratio

new_df.index = pd.DatetimeIndex(new_df.index)
new_df = new_df[new_df.index.month == 2]

ax = pandas_plot(new_df, fontsize=fontsize, day_interval=2)
ax.set_ylabel("Power (% of $P_{max}$)", fontsize=fontsize)
ax.set_ylim(0, 100)
ax.legend(new_df.columns, fontsize=fontsize)
plt.show()
