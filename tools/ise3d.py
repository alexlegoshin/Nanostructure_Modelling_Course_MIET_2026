# -*- coding: utf-8 -*-
"""Трёхмерные картинки лабы 3: каркас прибора и плоскость сечения внутри него.

Сечения делает сам ISE (`dfisetools -cut`) — он отдаёт обычную 2D-сетку.
Здесь она ставится обратно в объём и красится той же палитрой и той же
шкалой, что и плоские картинки (см. ise_style).
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation, LinearTriInterpolator
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection

import dfise
import ise_style as ise

MAGENTA = ise.MAGENTA
NB = len(ise.RGB)                      # 31 полоса
ZSTRETCH = 1.45                        # по Oz вытянуто, иначе прибор нечитаемо плоский


def _colors_on_grid(grid, vals, nu=160, nv=96):
    """Поле с треугольной сетки на регулярную, уже в виде цветов полос."""
    v = grid["vertices"]
    tri = Triangulation(v[:, 0], v[:, 1], dfise.triangles(grid))
    f = LinearTriInterpolator(tri, ise._t(vals))       # интерполируем преобразованное
    u = np.linspace(v[:, 0].min(), v[:, 0].max(), nu)
    w = np.linspace(v[:, 1].min(), v[:, 1].max(), nv)
    U, W = np.meshgrid(u, w)
    T = f(U, W)
    lo, hi = float(ise._t(vals).min()), float(ise._t(vals).max())
    if hi <= lo:
        hi = lo + 1.0
    k = np.clip(((np.ma.filled(T, lo) - lo) / (hi - lo) * NB).astype(int), 0, NB - 1)
    rgba = np.zeros(k.shape + (4,))
    for i in range(NB):
        rgba[k == i, :3] = ise.RGB[i]
    rgba[..., 3] = 1.0
    rgba[np.ma.getmaskarray(T), 3] = 0.0               # вне сетки — прозрачно
    return U, W, rgba


def cut_in_box(path, LX, LY, LZ, anode, grid, vals, kind,
               elev=20, azim=-135, width=348, height=276, zoom=1.05):
    """kind: 'y' — сечение поперёк прибора; 'x0.75' — вдоль, на заданном x."""
    U, W, C = _colors_on_grid(grid, vals)

    if kind == "y":
        X, Y, Z = -U, np.full_like(U, LY / 2.0), W
    else:
        X, Y, Z = np.full_like(U, float(kind[1:])), U, W

    fig = plt.figure(figsize=(width / 100.0, height / 100.0), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1], projection="3d")
    ax.plot_surface(X, Y, Z, facecolors=C, shade=False, rstride=1, cstride=1,
                    linewidth=0, antialiased=False)

    b = [(0, 0, 0), (LX, 0, 0), (LX, LY, 0), (0, LY, 0)]
    t = [(0, 0, LZ), (LX, 0, LZ), (LX, LY, LZ), (0, LY, LZ)]
    ax.add_collection3d(Line3DCollection(
        [[t[i], t[(i + 1) % 4]] for i in range(4)] + [[b[i], t[i]] for i in range(4)],
        colors="k", linewidths=1.0))
    ax.add_collection3d(Line3DCollection(
        [[b[i], b[(i + 1) % 4]] for i in range(4)], colors=[MAGENTA], linewidths=1.3))

    x0, y0, x1, y1 = anode
    r = [(x0, y0, LZ), (x1, y0, LZ), (x1, y1, LZ), (x0, y1, LZ)]
    ax.add_collection3d(Line3DCollection([[r[i], r[(i + 1) % 4]] for i in range(4)],
                                         colors=[MAGENTA], linewidths=1.3))

    if kind == "y":
        jl = [[(0, LY / 2.0, LZ / 2.0), (LX, LY / 2.0, LZ / 2.0)]]
    else:
        xx = float(kind[1:])
        jl = [[(xx, 0, LZ / 2.0), (xx, LY, LZ / 2.0)]]
    ax.add_collection3d(Line3DCollection(jl, colors="k", linewidths=1.2,
                                         linestyles="dashed"))

    ax.set_xlim(0, LX); ax.set_ylim(0, LY); ax.set_zlim(0, LZ)
    ax.set_box_aspect((LX, LY, LZ * ZSTRETCH), zoom=zoom)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.savefig(path, dpi=100, facecolor="white")
    plt.close(fig)
    return path


def structure(path, grd, dat, LX, LY, LZ, anode,
              elev=20, azim=-135, width=348, height=276, zoom=1.05):
    """Структура 3D-диода: поверхность с сеткой, крашеная по типу примеси.

    Синее — акцепторы (p, сторона анода), красное — доноры (n).
    Два цвета, а не радуга: примесь тут ступенькой, промежуточных значений нет.
    """
    g = dfise.read_grid3d(grd)
    dop = dfise.read_dataset(dat)["DopingConcentration"]
    return structure_surface(path, g["vertices"], g["surface"], dop, LX, LY, LZ, anode,
                             elev=elev, azim=azim, width=width, height=height, zoom=zoom)


def structure_surface(path, v, s, dop, LX, LY, LZ, anode,
                      elev=20, azim=-135, width=348, height=276, zoom=1.05, lw=0.2):
    """То же по готовой поверхности: v — вершины (мкм), s — треугольники, dop — примесь в вершинах.
    Так рисуется и сетка DEVSIM, не только DF-ISE."""
    fig = plt.figure(figsize=(width / 100.0, height / 100.0), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1], projection="3d")

    BLUE, RED = (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)
    faces = [[tuple(v[i]) for i in t] for t in s]
    cols = [BLUE if dop[t].mean() < 0 else RED for t in s]
    ax.add_collection3d(Poly3DCollection(faces, facecolors=cols,
                                         edgecolors="k", linewidths=lw))

    # контакты приподняты на волосок над гранью, иначе прячутся под ней
    e = LZ * 0.025
    x0, y0, x1, y1 = anode
    r = [(x0, y0, LZ + e), (x1, y0, LZ + e), (x1, y1, LZ + e), (x0, y1, LZ + e)]
    lc = Line3DCollection([[r[i], r[(i + 1) % 4]] for i in range(4)],
                          colors=[MAGENTA], linewidths=1.6)
    lc.set_zorder(10); ax.add_collection3d(lc)
    b = [(0, 0, -e), (LX, 0, -e), (LX, LY, -e), (0, LY, -e)]
    lc2 = Line3DCollection([[b[i], b[(i + 1) % 4]] for i in range(4)],
                           colors=[MAGENTA], linewidths=1.6)
    lc2.set_zorder(10); ax.add_collection3d(lc2)

    ax.set_xlim(0, LX); ax.set_ylim(0, LY); ax.set_zlim(0, LZ)
    ax.set_box_aspect((LX, LY, LZ * ZSTRETCH), zoom=zoom)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.savefig(path, dpi=100, facecolor="white")
    plt.close(fig)
    return path
