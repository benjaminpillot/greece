# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""
import numpy as np
from pandas import DataFrame
from gistools.layer import PolygonLayer

from greece.pfmtools.grid import Substation, PowerLine
from greece.pfmtools.power import BioPowerStation, TidalPowerStation, ThermalPowerStation, NuclearPowerStation, \
    SolarPowerStation, HydroPowerStation, GeothermalPowerStation, WindPowerStation, Storage, PowerStation

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2019, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


RTE_PWS_TECHNOLOGY = {}
RTE_PWS_TYPE = {"Autre": PowerStation, "Bioénergies": BioPowerStation, "Energies Marines": TidalPowerStation, "Eolien":
                WindPowerStation, "Géothermie": GeothermalPowerStation, "Hydraulique": HydroPowerStation, "Nucléaire":
                    NuclearPowerStation, "Solaire": SolarPowerStation, "Thermique non renouvelable":
                    ThermalPowerStation, "Stockage non hydraulique": Storage}


def rte_substations_with_power_plants(substations: Substation, power_lines: PowerLine, iris_layer: PolygonLayer,
                                      power_stations: DataFrame, cod_nat_key="codnat", iris_code_key="CODE_IRIS",
                                      voltage_key="voltage", power_key="power", pws_type_key=None, buffer=5):
    """ Retrieve which power stations are connected to French RTE network's substations
    
    Build French RTE substation layer with connected power stations.
    For those that are connected to 'nothing', build virtual substation
    :param substations: 
    :param power_lines: 
    :param iris_layer: 
    :param power_stations:
    :param cod_nat_key: 
    :param iris_code_key:
    :param voltage_key:
    :param power_key:
    :param pws_type_key: power station type key in pandas data frame
    :param buffer: buffer around virtual substation (in m)
    :return: new Substation class instance with added power stations
    """

    # Add power stations to substations through the CodNat code
    pw_station = power_stations[power_stations[cod_nat_key].isin(substations[cod_nat_key])]

    for i, cod_nat in enumerate(substations[cod_nat_key]):
        if cod_nat in pw_station[cod_nat_key].values:  # DO NOT forget the '.values': "in Series" returns False
            selected_pw_stations = pw_station[pw_station[cod_nat_key] == cod_nat]
            for _, r in selected_pw_stations.iterrows():
                substations.add_power_station(i, RTE_PWS_TYPE[r[pws_type_key]](r[power_key], r[voltage_key]))

    # Get other power stations with no corresponding CodNat code
    # Use IRIS code and voltage to get ending lines near given power station

    # Get substations with corresponding IRIS code info
    substations_with_iris = substations.sjoin(iris_layer, op="within")

    # Get power stations without substation and corresponding IRIS slice
    pw_station_with_no_substation = power_stations[~power_stations[cod_nat_key].isin(substations[cod_nat_key])]
    pw_with_no_sub_iris = iris_layer[iris_layer[iris_code_key].isin(pw_station_with_no_substation[iris_code_key])]

    # Get substations near power stations that are without corresponding substation
    substations_near_pwstation = substations.overlay(pw_with_no_sub_iris, how="intersect")

    # Get end of power lines that are not within substations
    ending_nodes, ending_nodes["pwline_id"] = power_lines.get_end_nodes()
    ending_nodes = ending_nodes.overlay(pw_with_no_sub_iris, how="intersect")
    ending_nodes = ending_nodes.overlay(substations_near_pwstation, how="difference")
    ending_nodes[voltage_key] = power_lines[voltage_key].iloc[ending_nodes["pwline_id"]].values
    ending_nodes = ending_nodes.drop_attribute("pwline_id")

    # Either add power station to existing substations or
    # create new virtual substation that hosts connection
    substations_with_pwstations = substations_with_iris.copy().append_attribute(type="real")
    for _, row in pw_station_with_no_substation.iterrows():
        iris, power, voltage, pws_type = row[[iris_code_key, power_key, voltage_key, pws_type_key]]
        add_pwstation = RTE_PWS_TYPE[pws_type](power, voltage)
        iris_and_voltage = (substations_with_pwstations[iris_code_key] == iris) & \
                           (substations_with_pwstations[voltage_key] == voltage)
        if iris_and_voltage.any():
            n = np.argwhere(iris_and_voltage.values).flatten()[0]  # Keep only first match
            substations_with_pwstations.add_power_station(n, add_pwstation)
        else:
            # Create virtual substation
            iris_and_voltage = (ending_nodes[iris_code_key] == iris) & (ending_nodes[voltage_key] == voltage)
            if iris_and_voltage.any():
                virtual_substation = ending_nodes[iris_and_voltage].dissolve(by=[iris_code_key, voltage_key])
                virtual_substation = virtual_substation.buffer(buffer).convex_hull().append_attribute(type="virtual")
                substations_with_pwstations = substations_with_pwstations.append(virtual_substation)
                substations_with_pwstations.add_power_station(substations_with_pwstations.index[-1], add_pwstation)

    return substations_with_pwstations


if __name__ == "__main__":
    import pandas as pd
    import os
    from greece import data_dir
    from utils.sys.timer import Timer

    with Timer() as t:
        power_stations = pd.read_csv(os.path.join(data_dir, "france_rte/list_power_stations.csv"), dtype=object)
        power_stations["voltage"] = power_stations["Tension raccordement"][~power_stations[
            "Tension raccordement"].isna()].apply(lambda x: x.replace(" ", ""))
        power_stations = power_stations.rename(index=str, columns={"codNat": "codnat"})
        power_stations["power"] = power_stations["puisMaxInstallee"].combine(power_stations["puisMaxRac"],
                                                                             lambda x, y: x if x != 0 else y)
        power_stations["CODE_IRIS"] = power_stations["CODE_IRIS"][~power_stations["CODE_IRIS"].isna()].apply(
            lambda x: str(int(x)))
    print("Pandas time: % s" % t)

    with Timer() as t:
        substations = Substation(os.path.join(data_dir, "france_rte/substations/substations.shp"), "tensionmax")
        substations = substations.rename("tensionmax", "voltage")
        pwlines = PowerLine(os.path.join(data_dir, "france_rte/france_pwlines/france_pwlines.shp"), "tension")
        pwlines = pwlines.rename("tension", "voltage")
    print("Substation time: %s" % t)

    with Timer() as t:
        iris = PolygonLayer(os.path.join(data_dir, "iris/iris.shp"))
    print("IRIS time: %s" % t)

    with Timer() as t:
        power_stations = power_stations[power_stations["CODE_IRIS"].isin(iris["CODE_IRIS"])]
        power_stations = power_stations[~power_stations["codnat"].isna()]
        power_stations = power_stations[power_stations["regime"] == "En service"]
    print("Power station time: %s" % t)

    with Timer() as t:
        france_substations = rte_substations_with_power_plants(substations, pwlines, iris,
                                                               power_stations, pws_type_key="Filière")
    print("Finalization time: %s" % t)

    france_substations["NbPwsCon"] = [len(sub) for sub in france_substations.substation]
    france_substations.to_file("/home/benjamin/Desktop/RTE_substations")
