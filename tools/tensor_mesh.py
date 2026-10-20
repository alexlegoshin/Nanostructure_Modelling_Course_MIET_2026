# -*- coding: utf-8 -*-
"""Тетраэдрическая сетка из тензорной: каждый прямоугольный параллелепипед — 6 тетраэдров.

Зачем: у сетки ISE все узлы лежат на прямоугольной решётке, и её ячейки Вороного —
прямоугольные коробки. Тензорная сетка, разрезанная по Куну (6 тетраэдров с общей
диагональю), даёт то же самое: грани ячеек — точные прямоугольники, площади
неотрицательны, объём сходится в точности. Сгущая оси, получаем последовательность
сеток «как у ISE» для проверки сходимости по сетке.

Оси строятся от узлов сетки ISE (все различные x, y, z — их тензорное произведение
уже мельче самой сетки ISE) с делением каждого отрезка на `split` частей.

Формат результата — как у tools/ise_grid.load(): vertices (мкм), bulk, contacts,
donors, acceptors — его понимает tools/dev_ise.mesh_from_ise().
"""
import numpy as np

# 6 тетраэдров Куна в кубе с вершинами (i,j,k) = биты 0..7: все проходят по диагонали 0-7
KUHN = ((0, 1, 3, 7), (0, 1, 5, 7), (0, 2, 3, 7), (0, 2, 6, 7), (0, 4, 5, 7), (0, 4, 6, 7))


def refine(axis, split):
    axis = np.asarray(sorted(set(np.round(axis, 9))))
    if split <= 1:
        return axis
    out = [axis[0]]
    for a, b in zip(axis[:-1], axis[1:]):
        out += list(a + (b - a) * np.arange(1, split + 1) / split)
    return np.array(out)


def build(xs, ys, zs, anode, NA=1.4e17, ND=1.0e17, zj=0.4):
    """anode = (x0, y0, x1, y1) на верхней грани z = max(zs); катод — вся нижняя грань."""
    xs, ys, zs = (np.asarray(sorted(set(np.round(a, 9)))) for a in (xs, ys, zs))
    for v, ax in ((anode[0], xs), (anode[2], xs), (anode[1], ys), (anode[3], ys), (zj, zs)):
        if not np.any(np.isclose(ax, v)):
            raise ValueError("граница %g не лежит на оси — анод/переход разъедется" % v)
    nx, ny, nz = len(xs), len(ys), len(zs)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    idx = np.arange(nx * ny * nz).reshape(nx, ny, nz)

    corner = []                            # номера 8 вершин каждого параллелепипеда, бит = (i, j, k)
    for b in range(8):
        i, j, k = (b >> 2) & 1, (b >> 1) & 1, b & 1
        corner.append(idx[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k].ravel())
    corner = np.stack(corner, axis=1)
    # KUHN задан в битах (x=4, y=2, z=1)
    tets = np.concatenate([corner[:, list(t)] for t in KUHN])

    def face_tris(mask_k, kk):
        """Треугольники грани z = zs[kk] там, где mask_k (по квадратам) — по диагонали, как у Куна."""
        out = []
        q = np.argwhere(mask_k)
        for i, j in q:
            a, b, c, d = idx[i, j, kk], idx[i + 1, j, kk], idx[i, j + 1, kk], idx[i + 1, j + 1, kk]
            out += [(a, b, d), (a, c, d)]     # диагональ a-d совпадает с гранями тетраэдров Куна
        return np.array(out, dtype=np.int64)

    xc, yc = 0.5 * (xs[:-1] + xs[1:]), 0.5 * (ys[:-1] + ys[1:])
    in_anode = ((xc[:, None] > anode[0]) & (xc[:, None] < anode[2]) &
                (yc[None, :] > anode[1]) & (yc[None, :] < anode[3]))
    contacts = {"Anode": ("Contact", face_tris(in_anode, nz - 1)),
                "Cathode": ("Contact", face_tris(np.ones((nx - 1, ny - 1), bool), 0))}
    z = verts[:, 2]
    eps = 1e-9
    acc = np.where(z >= zj - eps, NA, 0.0)       # узлы на самом переходе — с обоими, как у ISE
    don = np.where(z <= zj + eps, ND, 0.0)
    return {"vertices": verts, "bulk": {"SiW": ("Silicon", tets.astype(np.int64))},
            "contacts": contacts, "donors": don, "acceptors": acc, "net": don - acc}


def from_ise(grid, split=1, anode=(0.0, 1.0, 1.0, 2.0), lz=0.8):
    """lz — толщина прибора, мкм: оси ISE по z растягиваются в lz/0.8 раза, переход — посередине.
    lz = 2 — базовая структура методички (до деления на k = 2/d по варианту)."""
    v = grid["vertices"]
    k = lz / 0.8
    return build(refine(v[:, 0], split), refine(v[:, 1], split), refine(v[:, 2] * k, split), anode,
                 zj=lz / 2)


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ise_grid
    g = ise_grid.load(sys.argv[1], sys.argv[2])
    for s in (1, 2, 3):
        t = from_ise(g, s)
        v, (_, tt) = t["vertices"], t["bulk"]["SiW"]
        vol = ise_grid.tet_volumes(v, tt).sum()
        print("split %d: узлов %d, тетраэдров %d, объём %.4f, анод %d треуг., катод %d"
              % (s, len(v), len(tt), vol, len(t["contacts"]["Anode"][1]), len(t["contacts"]["Cathode"][1])))
