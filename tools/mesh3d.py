# -*- coding: utf-8 -*-
"""Сетка 3D-диода в Gmsh для DEVSIM.

Переход и анод встроены в геометрию как поверхности: ступенька легирования
и край контакта ложатся точно на узлы, а не размазываются между ними.
Сгущение — тремя полями расстояний: к плоскости перехода, к аноду и отдельно
к краю анода, где поле особенное (из-за него ISE и не взял диод B).

Строим в микронах, сохраняем в сантиметрах — DEVSIM считает в см.
"""

import gmsh


def build(path, anode=(0.0, 1.0, 1.0, 2.0), LX=1.0, LY=3.0, LZ=0.8,
          h_far=0.10, h_junc=0.012, h_anode=0.015, h_edge=0.006, verbose=False):
    x0, y0, x1, y1 = anode
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1 if verbose else 0)
    gmsh.model.add("diode3d")
    occ = gmsh.model.occ

    box = occ.addBox(0, 0, 0, LX, LY, LZ)
    junc = occ.addRectangle(0, 0, LZ / 2, LX, LY)          # плоскость перехода
    anod = occ.addRectangle(x0, y0, LZ, x1 - x0, y1 - y0)  # прямоугольник анода
    occ.fragment([(3, box)], [(2, junc), (2, anod)])
    occ.synchronize()

    # опознаём поверхности по габаритам
    eps = 1e-6
    def surfs(test):
        out = []
        for dim, tag in gmsh.model.getEntities(2):
            bb = gmsh.model.getBoundingBox(dim, tag)
            if test(bb): out.append(tag)
        return out
    anode_s = surfs(lambda b: abs(b[2]-LZ) < eps and abs(b[5]-LZ) < eps
                    and b[0] > x0-eps and b[3] < x1+eps and b[1] > y0-eps and b[4] < y1+eps)
    cath_s  = surfs(lambda b: abs(b[2]) < eps and abs(b[5]) < eps)
    junc_s  = surfs(lambda b: abs(b[2]-LZ/2) < eps and abs(b[5]-LZ/2) < eps)
    vols = [t for d, t in gmsh.model.getEntities(3)]

    gmsh.model.addPhysicalGroup(3, vols, name="silicon")
    gmsh.model.addPhysicalGroup(2, anode_s, name="anode")
    gmsh.model.addPhysicalGroup(2, cath_s, name="cathode")

    # кромки анода — именно там особенность поля
    edges = set()
    for s in anode_s:
        for d, c in gmsh.model.getBoundary([(2, s)], oriented=False):
            edges.add(c)

    f = gmsh.model.mesh.field
    def thr(src_dim, tags, hmin, hmax, dmin, dmax):
        dist = f.add("Distance")
        f.setNumbers(dist, "SurfacesList" if src_dim == 2 else "CurvesList", list(tags))
        f.setNumber(dist, "Sampling", 120)
        t = f.add("Threshold")
        f.setNumber(t, "InField", dist)
        f.setNumber(t, "SizeMin", hmin); f.setNumber(t, "SizeMax", hmax)
        f.setNumber(t, "DistMin", dmin); f.setNumber(t, "DistMax", dmax)
        return t
    fields = [thr(2, junc_s, h_junc, h_far, 0.02, 0.25),
              thr(2, anode_s, h_anode, h_far, 0.02, 0.30),
              thr(1, edges, h_edge, h_far, 0.01, 0.30)]
    fmin = f.add("Min"); f.setNumbers(fmin, "FieldsList", fields)
    f.setAsBackgroundMesh(fmin)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.Algorithm3D", 10)            # HXT, быстрый и качественный
    gmsh.option.setNumber("Mesh.Optimize", 1)

    gmsh.model.mesh.generate(3)
    gmsh.model.mesh.affineTransform([1e-4, 0, 0, 0, 0, 1e-4, 0, 0, 0, 0, 1e-4, 0])
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)        # DEVSIM читает только v2
    gmsh.write(path)

    nodes = len(gmsh.model.mesh.getNodes()[0])
    et, _, _ = gmsh.model.mesh.getElements(3)
    ntet = sum(len(t) for t in gmsh.model.mesh.getElements(3)[1])
    gmsh.finalize()
    return {"nodes": nodes, "tets": ntet, "anode": anode_s, "cathode": cath_s,
            "junction": junc_s, "edges": len(edges)}
