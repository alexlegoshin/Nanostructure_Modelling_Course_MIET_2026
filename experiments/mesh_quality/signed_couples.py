# -*- coding: utf-8 -*-
"""Площади граней Вороного со знаком против DEVSIM: суммы объёмов и сравнение по рёбрам.

    python signed_couples.py ise A
    python signed_couples.py gmsh ..\..\Lab3_diode_3D\devsim\mesh_A_2.5.msh
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import voronoi3d


def load(kind, what):
    if kind == "ise":
        import ise_grid
        ise = os.path.join(HERE, "..", "..", "Lab3_diode_3D", "ise")
        g = ise_grid.read_tet_grid(os.path.join(ise, "s%s_msh.grd" % what))
        (_, tets), = g["bulk"].values()
        return g["vertices"], tets
    import gmsh
    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0); gmsh.open(what)
    tags, xyz, _ = gmsh.model.mesh.getNodes()
    order = np.argsort(tags); xyz = xyz.reshape(-1, 3)[order] * 1e4      # см -> мкм
    pos = {int(t): k for k, t in enumerate(tags[order])}
    tets = []
    for et, _, nodes in zip(*gmsh.model.mesh.getElements(3)):
        if et == 4:
            tets.append(np.vectorize(pos.get)(nodes.reshape(-1, 4)))
    gmsh.finalize()
    return xyz, np.concatenate(tets)


def main():
    v, t = load(sys.argv[1], sys.argv[2])
    a, b, c, d = (v[t[:, k]] for k in range(4))
    vol = np.abs(np.einsum("ij,ij->i", b - a, np.cross(c - a, d - a))) / 6
    edges, signed, absval = voronoi3d.couples(v, t)
    L = np.linalg.norm(v[edges[:, 1]] - v[edges[:, 0]], axis=1)
    print("тетраэдров %d, объём %.4f мкм³" % (len(t), vol.sum()))
    print("сумма A·L/3: со знаком %.4f, по модулю %.4f мкм³" % ((signed * L).sum() / 3, (absval * L).sum() / 3))
    print("рёбер с отрицательной суммарной площадью: %d из %d" % ((signed < 0).sum(), len(signed)))


if __name__ == "__main__":
    main()
