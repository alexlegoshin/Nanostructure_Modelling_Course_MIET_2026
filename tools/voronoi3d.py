# -*- coding: utf-8 -*-
"""Коэффициенты метода контрольных объёмов на тетраэдрах: площади граней ячеек Вороного.

Для ребра ij тетраэдра его кусок грани Вороного — четырёхугольник: середина ребра,
центры описанных окружностей двух граней, прилегающих к ребру, и центр описанной
сферы тетраэдра. Площадь берётся СО ЗНАКОМ (проекция на направление ребра): если
центр сферы вне тетраэдра, часть вкладов отрицательна и гасит лишнее у соседей.
Со знаками сумма A·L/3 по всем рёбрам равна объёму тетраэдра в точности.

Зачем: DEVSIM 2.11 в 3D складывает эти вклады по модулю — на сетке ISE диода A его
объём ячеек 3.06 мкм³ вместо 2.4, на сетке Gmsh — 4.54. Проводимость рёбер завышена
так же, и ток выходит выше настоящего (experiments/mesh_quality).
"""
import numpy as np

EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
# для ребра (a, b) — две оставшиеся вершины; каждая с ребром задаёт прилегающую грань
OTHER = {(0, 1): (2, 3), (0, 2): (1, 3), (0, 3): (1, 2), (1, 2): (0, 3), (1, 3): (0, 2), (2, 3): (0, 1)}


def _circ_tri(a, b, c):
    """Центр описанной окружности треугольника (в его плоскости), векторно по строкам."""
    ab, ac = b - a, c - a
    n = np.cross(ab, ac)
    nn = np.einsum("ij,ij->i", n, n)
    return a + (np.cross(n, ab) * np.einsum("ij,ij->i", ac, ac)[:, None]
                + np.cross(ac, n) * np.einsum("ij,ij->i", ab, ab)[:, None]) / (2 * nn[:, None])


def _circ_tet(p0, p1, p2, p3):
    A = np.stack([p1 - p0, p2 - p0, p3 - p0], axis=1)            # (m, 3, 3)
    rhs = 0.5 * np.stack([np.einsum("ij,ij->i", d, d) for d in (p1 - p0, p2 - p0, p3 - p0)], axis=1)
    return p0 + np.linalg.solve(A, rhs[..., None])[..., 0]


def read_msh(path):
    """Вершины (мкм) и тетраэдры из .msh, записанного tools/mesh3d.py (там координаты в см)."""
    import gmsh
    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0); gmsh.open(path)
    tags, xyz, _ = gmsh.model.mesh.getNodes()
    order = np.argsort(tags)
    xyz = xyz.reshape(-1, 3)[order] * 1e4
    pos = np.zeros(int(tags.max()) + 1, dtype=np.int64); pos[tags[order].astype(np.int64)] = np.arange(len(order))
    tets = [pos[n.astype(np.int64)].reshape(-1, 4)
            for et, _, n in zip(*gmsh.model.mesh.getElements(3)) if et == 4]
    gmsh.finalize()
    return xyz, np.concatenate(tets)


def couples(verts, tets):
    """Площади граней Вороного по рёбрам, со знаком. Возвращает (рёбра (k,2), площади (k,))."""
    P = [verts[tets[:, i]] for i in range(4)]
    cc = _circ_tet(*P)
    keys, vals = [], []
    for a, b in EDGES:
        c, d = OTHER[(a, b)]
        m = 0.5 * (P[a] + P[b])
        e = P[b] - P[a]
        e = e / np.linalg.norm(e, axis=1)[:, None]
        fc = _circ_tri(P[a], P[b], P[c])
        fd = _circ_tri(P[a], P[b], P[d])
        # два треугольника (m, fc, cc) и (m, cc, fd), площадь — проекция на направление ребра;
        # ориентация выбрана так, чтобы у хорошо центрированного тетраэдра площадь была > 0
        s = 0.5 * np.einsum("ij,ij->i", np.cross(fc - m, cc - m), e) \
            + 0.5 * np.einsum("ij,ij->i", np.cross(cc - m, fd - m), e)
        # знак ориентации зависит от того, с какой стороны ребра лежат c и d — нормируем
        side = np.einsum("ij,ij->i", np.cross(P[c] - P[a], P[d] - P[a]), e)
        s = s * np.sign(side)
        i, j = tets[:, a], tets[:, b]
        keys.append(np.stack([np.minimum(i, j), np.maximum(i, j)], axis=1))
        vals.append(s)
    keys = np.concatenate(keys); vals = np.concatenate(vals)
    uniq, inv = np.unique(keys, axis=0, return_inverse=True)
    return uniq, np.bincount(inv.ravel(), weights=vals), np.bincount(inv.ravel(), weights=np.abs(vals))
