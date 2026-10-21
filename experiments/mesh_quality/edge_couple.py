# -*- coding: utf-8 -*-
"""Качество тетраэдрической сетки для метода контрольных объёмов: отрицательные EdgeCouple.

Поток по ребру в DEVSIM (и в ISE) умножается на EdgeCouple — площадь грани ячейки
Вороного, через которую идёт поток. На сетке Делоне все EdgeCouple >= 0. На
не-Делоне часть из них отрицательна: ток по такому ребру течёт «против» разности
потенциалов, и решение искажается — для прибора это лишняя проводимость.

    python edge_couple.py ise A                         # сетка ISE диода A
    python edge_couple.py gmsh ..\..\Lab3_diode_3D\devsim\mesh_A_2.5.msh
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import devsim as ds


def main():
    kind, what = sys.argv[1], sys.argv[2]
    if kind == "ise":
        import ise_grid, dev_ise
        ise = os.path.join(HERE, "..", "..", "Lab3_diode_3D", "ise")
        g = ise_grid.load(os.path.join(ise, "s%s_msh.grd" % what), os.path.join(ise, "s%s_msh.dat" % what))
        dev_ise.create_device(dev_ise.mesh_from_ise(g), g["donors"], g["acceptors"])
    else:
        ds.create_gmsh_mesh(mesh="m", file=what)
        ds.add_gmsh_region(gmsh_name="silicon", mesh="m", region="si", material="Silicon")
        for c in ("anode", "cathode"):
            ds.add_gmsh_contact(gmsh_name=c, region="si", name=c, mesh="m", material="metal")
        ds.finalize_mesh(mesh="m"); ds.create_device(mesh="m", device="diode")
    ec = np.array(ds.get_edge_model_values(device="diode", region="si", name="EdgeCouple"))
    el = np.array(ds.get_edge_model_values(device="diode", region="si", name="EdgeLength"))
    nv = len(ds.get_node_model_values(device="diode", region="si", name="NodeVolume"))
    vol = np.array(ds.get_node_model_values(device="diode", region="si", name="NodeVolume"))
    print("объём: сумма NodeVolume %.4f мкм³, сумма EdgeCouple·L/3 %.4f мкм³ (прибор 2.4)"
          % (vol.sum() * 1e12, (ec * el).sum() / 3 * 1e12))
    g = ec / el                       # проводимость ребра ~ EdgeCouple / длина
    neg = ec < 0
    print("узлов %d, рёбер %d" % (nv, len(ec)))
    print("отрицательных EdgeCouple: %d (%.2f %%), их доля в сумме |EdgeCouple/L|: %.2f %%"
          % (neg.sum(), 100 * neg.mean(), 100 * np.abs(g[neg]).sum() / np.abs(g).sum()))
    if neg.any():
        print("самая отрицательная связь: %.3g от медианы положительных" % (g[neg].min() / np.median(g[~neg])))


if __name__ == "__main__":
    main()
