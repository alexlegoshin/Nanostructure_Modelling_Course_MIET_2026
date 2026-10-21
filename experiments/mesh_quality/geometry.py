# -*- coding: utf-8 -*-
"""Геометрия сетки, как её видит DEVSIM: объём, площади контактов, узлы на переходе.

    python geometry.py ise A
    python geometry.py gmsh ..\..\Lab3_diode_3D\devsim\mesh_A_2.5.msh
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import devsim as ds
import dev_ise


def main():
    kind, what = sys.argv[1], sys.argv[2]
    if kind == "ise":
        import ise_grid
        ise = os.path.join(HERE, "..", "..", "Lab3_diode_3D", "ise")
        g = ise_grid.load(os.path.join(ise, "s%s_msh.grd" % what), os.path.join(ise, "s%s_msh.dat" % what))
        dev_ise.create_device(dev_ise.mesh_from_ise(g), g["donors"], g["acceptors"])
    else:
        ds.create_gmsh_mesh(mesh="m", file=what)
        dev_ise.create_device("m", junction=(1.4e17, 1.0e17, 0.4e-4))
    D, R = dev_ise.DEV, dev_ise.REG
    vol = np.array(ds.get_node_model_values(device=D, region=R, name="NodeVolume"))
    z = np.array(ds.get_node_model_values(device=D, region=R, name="z"))
    don = np.array(ds.get_node_model_values(device=D, region=R, name="Donors"))
    acc = np.array(ds.get_node_model_values(device=D, region=R, name="Acceptors"))
    print("объём %.4f мкм³ (должно 2.4)" % (vol.sum() * 1e12))
    both = (don > 0) & (acc > 0)
    print("узлов с обоими легированиями: %d, их объём %.4f мкм³; z таких узлов: %s"
          % (both.sum(), vol[both].sum() * 1e12, np.unique(np.round(z[both] * 1e4, 4))[:5]))
    for c in ("anode", "cathode"):
        a = np.array(ds.get_node_model_values(device=D, region=R, name="SurfaceArea"))
        nodes = ds.get_element_node_list(device=D, region=R, contact=c)
        idx = np.unique(np.array(nodes).ravel())
        print("%-8s узлов %d, площадь %.4f мкм²" % (c, len(idx), a[idx].sum() * 1e8))


if __name__ == "__main__":
    main()
