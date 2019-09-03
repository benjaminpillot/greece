# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

__version__ = '0.1'
__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
ghi = pd.read_csv("/home/benjamin/ownCloud/Post-doc Guyane/GREECE model/Results/Solar "
                  "GHI/hourly_ghi_permissive_contour.csv",
                  index_col=0)
pv = pd.read_csv("/home/benjamin/ownCloud/Post-doc Guyane/GREECE model/Results/Solar "
                 "PV/output_ac_power_permissive_contour.csv")
power_sum_no_frac = 0
power_sum_frac = 0
for poly, power in zip([5, 54, 57, 67, 78, 81], [19949, 17756, 1383, 2360, 2891, 14244]):
    power_sum_no_frac += pv["polygon %d" % poly] * power/6003.72
for poly, power in zip([10, 28, 54, 71, 76, 78], [15493, 14576, 17293, 5338, 3478, 2891]):
    power_sum_frac += pv["polygon %d" % poly] * power/6003.72

print("sum no frac: %.3f" % np.sum(power_sum_no_frac))
print("sum frac: %.3f" % np.sum(power_sum_frac))
print("MBE: %.3f" % np.mean(power_sum_no_frac - power_sum_frac))


power_sum_no_frac.plot(color="red")
power_sum_frac.plot(color="blue")
plt.show()

# polygons = {}
# for poly, color in zip([48, 41, 98, 10, 21], ["green", "blue", "red", "purple", "yellow"]):
#     polygons[poly] = ghi["polygon %d" % poly]
#     polygons[poly].index = pd.DatetimeIndex(polygons[poly].index)
#     polygons[poly] = polygons[poly][polygons[poly].index.month == 2]
#
#     ax = polygons[poly].plot(x_compat=True, color=color)
#     ax.set_ylabel("Solar GHI (Wh/m^2)")
#     ax.set_xlim(polygons[poly].index[0], polygons[poly].index[-1] + pd.Timedelta("1h"))
#     ax.set_ylim(0, 1000)
#
#     plt.show()
#
#     print("Polygon %d: %.3f" % (poly, polygons[poly].sum()))
#
# polygons[10].plot(color="blue")
# polygons[21].plot(color="green")
# plt.show()
#
# print("Corrrelation: %.3f" % polygons[10].corr(polygons[21]))
