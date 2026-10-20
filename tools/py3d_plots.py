# -*- coding: utf-8 -*-
"""Картинки по результатам своего решателя и DEVSIM — в том же стиле, что и ISE-овские.

Свой решатель (dd3d) — тензорная сетка, поля массивами [x, y, z].
DEVSIM — тетраэдры, поля в узлах (devsim/run.py пишет их в field_*.npz).
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Line3DCollection

import ise_style as ise
import ise3d

Q = 1.602176634e-19


def charge(z):
    """Плотность заряда в тех же единицах, что у ISE: 1/см3, не Кл/см3."""
    return z["p"] - z["n"] + z["C"]


def cut_plane(z, kind, value, fine=5):
    """Срез тензорной сетки. fine — во сколько раз сгустить для гладкой заливки:
    расчётная сетка неравномерная и редкая, без этого полосы выходят ступеньками."""
    q = charge(z)
    if kind == "y":
        j = int(np.argmin(np.abs(z["y"] - value * 1e-4)))
        u, w, F = z["x"] * 1e4, z["z"] * 1e4, q[:, j, :]
    else:
        j = int(np.argmin(np.abs(z["x"] - value * 1e-4)))
        u, w, F = z["y"] * 1e4, z["z"] * 1e4, q[j, :, :]
    if fine > 1:
        from scipy.interpolate import RegularGridInterpolator
        f = RegularGridInterpolator((u, w), F, method="linear")
        u2 = np.linspace(u[0], u[-1], len(u) * fine)
        w2 = np.linspace(w[0], w[-1], len(w) * fine)
        U, W = np.meshgrid(u2, w2, indexing="ij")
        F = f(np.stack([U.ravel(), W.ravel()], axis=1)).reshape(U.shape)
        u, w = u2, w2
    return u, w, F


def j_top(path_npz, anode, LZ=0.8):
    """Плотность тока вдоль верхней границы сечения y=1.5.

    Считается тем же потоком Шарфеттера-Гуммеля, что и в решателе, по рёбрам,
    упирающимся в верхнюю грань — иначе одностороняя разность на мелкой ячейке
    завышает результат на порядок.
    """
    import dd3d
    z = np.load(path_npz)
    psi, n, p, C = z["psi"], z["n"], z["p"], z["C"]
    x, y, zz = z["x"], z["y"], z["z"]
    j = int(np.argmin(np.abs(y - 1.5e-4)))
    k = len(zz) - 1
    h = zz[k] - zz[k - 1]
    d = (psi[:, j, k] - psi[:, j, k - 1]) / dd3d.VT
    Nt = 0.5 * (np.abs(C[:, j, k]) + np.abs(C[:, j, k - 1]))
    E = (psi[:, j, k] - psi[:, j, k - 1]) / h
    mn = dd3d.mu_field(dd3d.mu_doping(Nt, "n"), E, "n")
    mp = dd3d.mu_field(dd3d.mu_doping(Nt, "p"), E, "p")
    Jn = Q * mn * dd3d.VT / h * (n[:, j, k] * dd3d.bern(d) - n[:, j, k - 1] * dd3d.bern(-d))
    Jp = Q * mp * dd3d.VT / h * (p[:, j, k - 1] * dd3d.bern(d) - p[:, j, k] * dd3d.bern(-d))
    inside = (x * 1e4 >= anode[0] - 1e-9) & (x * 1e4 <= anode[2] + 1e-9)
    return x * 1e4, np.where(inside, np.abs(Jn + Jp), 0.0)


def cut_in_box(path, z, kind, value, LX=1.0, LY=3.0, LZ=0.8, anode=(0, 1, 1, 2),
               elev=16, azim=-64, width=348, height=276, zoom=1.25, uwF=None):
    """Плоскость сечения внутри каркаса прибора — как у ise3d, но из наших полей.
    uwF — готовый срез (ось1, ось2, поле), например devsim_cut(); тогда z не нужен."""
    u, w, F = uwF if uwF is not None else cut_plane(z, kind, value)
    t = ise._t(F)
    lo, hi = float(t.min()), float(t.max())
    if hi <= lo:
        hi = lo + 1.0
    nb = len(ise.RGB)
    k = np.clip(((t - lo) / (hi - lo) * nb).astype(int), 0, nb - 1)
    C = np.zeros(k.shape + (4,)); C[..., 3] = 1.0
    for i in range(nb):
        C[k == i, :3] = ise.RGB[i]

    U, W = np.meshgrid(u, w, indexing="ij")
    if kind == "y":
        X, Y, Z = U, np.full_like(U, value), W
    else:
        X, Y, Z = np.full_like(U, value), U, W

    fig = plt.figure(figsize=(width / 100.0, height / 100.0), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1], projection="3d")
    ax.plot_surface(X, Y, Z, facecolors=C, shade=False, rstride=1, cstride=1,
                    linewidth=0, antialiased=False)

    b = [(0, 0, 0), (LX, 0, 0), (LX, LY, 0), (0, LY, 0)]
    tp = [(0, 0, LZ), (LX, 0, LZ), (LX, LY, LZ), (0, LY, LZ)]
    ax.add_collection3d(Line3DCollection(
        [[tp[i], tp[(i + 1) % 4]] for i in range(4)] + [[b[i], tp[i]] for i in range(4)],
        colors="k", linewidths=1.0))
    ax.add_collection3d(Line3DCollection([[b[i], b[(i + 1) % 4]] for i in range(4)],
                                         colors=[ise.MAGENTA], linewidths=1.3))
    x0, y0, x1, y1 = anode
    r = [(x0, y0, LZ), (x1, y0, LZ), (x1, y1, LZ), (x0, y1, LZ)]
    ax.add_collection3d(Line3DCollection([[r[i], r[(i + 1) % 4]] for i in range(4)],
                                         colors=[ise.MAGENTA], linewidths=1.3))
    jl = ([[(0, value, LZ / 2), (LX, value, LZ / 2)]] if kind == "y"
          else [[(value, 0, LZ / 2), (value, LY, LZ / 2)]])
    ax.add_collection3d(Line3DCollection(jl, colors="k", linewidths=1.2,
                                         linestyles="dashed"))

    ax.set_xlim(0, LX); ax.set_ylim(0, LY); ax.set_zlim(0, LZ)
    ax.set_box_aspect((LX, LY, LZ), zoom=zoom)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.savefig(path, dpi=100, facecolor="white")
    plt.close(fig)
    return path


# ---------------------------------------------------------------- DEVSIM

def devsim_surface(zd):
    """Внешние треугольники тетраэдральной сетки: грань, принадлежащая одному тетраэдру."""
    t = zd["tets"]
    f = np.concatenate([t[:, [0, 1, 2]], t[:, [0, 1, 3]], t[:, [0, 2, 3]], t[:, [1, 2, 3]]])
    key = np.sort(f, axis=1)
    _, idx, cnt = np.unique(key, axis=0, return_index=True, return_counts=True)
    return f[idx[cnt == 1]]


def devsim_structure(path, zd, LX=1.0, LY=3.0, LZ=0.8, anode=(0, 1, 1, 2)):
    """Структура по сетке Gmsh/DEVSIM: поверхность с сеткой, синее — p, красное — n."""
    v = np.stack([zd["x"], zd["y"], zd["z"]], axis=1) * 1e4
    # сетка Gmsh у анода и перехода в разы гуще ISE-овской — линии тоньше, иначе сплошь чёрное
    return ise3d.structure_surface(path, v, devsim_surface(zd), zd["C"], LX, LY, LZ, anode, lw=0.05)


def tet_interp(zd, vals, P, k=24):
    """Линейная интерполяция по настоящим тетраэдрам сетки, а не по своей триангуляции.

    LinearNDInterpolator строит Делоне поверх облака узлов, и его тетраэдры-щепки
    тянут значения через ступеньку легирования — на срезе выходят ложные полосы.
    Здесь для каждой точки ищется содержащий её тетраэдр сетки (среди k ближайших
    по центру), значение — по барицентрическим координатам.
    """
    from scipy.spatial import cKDTree
    t = zd["tets"]
    r = np.stack([zd["x"], zd["y"], zd["z"]], 1) * 1e4
    R0 = r[t[:, 0]]
    M = np.linalg.inv(np.transpose(r[t[:, 1:]] - R0[:, None, :], (0, 2, 1)))   # (T,3,3)
    _, cand = cKDTree(r[t].mean(1)).query(P, k=k)
    out = np.full(len(P), np.nan)
    best = np.full(len(P), -np.inf)
    for j in range(k):
        c = cand[:, j]
        lam = np.einsum("pij,pj->pi", M[c], P - R0[c])
        l = np.concatenate([1 - lam.sum(1, keepdims=True), lam], 1)          # (P,4)
        worst = l.min(1)                       # >= 0 — точка внутри (или на грани)
        better = worst > best
        val = (l * vals[t[c]]).sum(1)
        out = np.where(better, val, out); best = np.where(better, worst, best)
    return out


def devsim_cut(zd, kind, value, nu=120, nw=96):
    """Срез тетраэдральной сетки на регулярную решётку.

    Интерполяция в преобразованной шкале (ареасинус), а не по самому заряду —
    как у picasso с interpol arsinh: заряд гуляет на 17 порядков, и линейная
    интерполяция по значению протягивает большие величины через переход.
    """
    pts = np.stack([zd["x"], zd["y"], zd["z"]], axis=1) * 1e4
    if kind == "y":
        u = np.linspace(pts[:, 0].min(), pts[:, 0].max(), nu)
    else:
        u = np.linspace(pts[:, 1].min(), pts[:, 1].max(), nu)
    w = np.linspace(pts[:, 2].min(), pts[:, 2].max(), nw)
    U, W = np.meshgrid(u, w, indexing="ij")
    P = (np.stack([U, np.full_like(U, value), W], -1) if kind == "y"
         else np.stack([np.full_like(U, value), U, W], -1))
    T = tet_interp(zd, ise._t(charge(zd)), P.reshape(-1, 3)).reshape(U.shape)
    return u, w, ise.ARSINH_A * np.sinh(T)


def devsim_j_top(path_npz, anode, LZ=0.8, y=1.5, nx=101, sx=0.04, sy=0.1):
    """|J| на верхней грани вдоль линии y=1.5 по полям DEVSIM.

    Берётся ток узлов из run.py (node_current): поток по рёбрам элементов,
    умноженный на площадь граней контрольного объёма, — ровно то, что решал DEVSIM;
    его сумма по узлам анода равна току контакта. Площадь узла — ContactSurfaceArea
    самого DEVSIM (если сохранена), иначе треть прилегающих треугольников грани.

    Поузловое отношение ток/площадь на неструктурированной сетке шумит на десятки
    процентов: доля тока, доставшаяся узлу, зависит от его связей в сетке. Поэтому
    J(x) = sum(I_i w_i) / sum(A_i w_i) с гауссовым окном sx по x и sy по y — ток при
    этом не теряется, разрешение по x около sx.

    Восстанавливать вектор J из полей или из потоков по рёбрам тетраэдра нельзя:
    проверено, ток через горизонтальные сечения тогда «гуляет» вдвое.
    """
    zd = np.load(path_npz)
    r = np.stack([zd["x"], zd["y"], zd["z"]], 1) * 1e4
    nc = zd["node_current"]
    on_top = np.abs(r[:, 2] - LZ) < 1e-7
    if "area" in zd.files:
        A = np.where(on_top, zd["area"], 0.0)
    else:
        f = devsim_surface(zd)
        f = f[on_top[f].all(1)]
        P = r[f][..., :2]
        e1, e2 = P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]
        area = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) * 1e-8   # см2
        A = np.zeros(len(nc))
        for k in range(3):
            np.add.at(A, f[:, k], area / 3.0)
    m = on_top & (A > 0)
    xi, yi, Ii, Ai = r[m, 0], r[m, 1], np.abs(nc[m]), A[m]
    xs = np.linspace(0.0, 1.0, nx)
    w = np.exp(-0.5 * ((xs[:, None] - xi[None]) / sx) ** 2 - 0.5 * ((y - yi[None]) / sy) ** 2)
    x0, y0, x1, y1 = anode
    inside = (xs >= x0 - 1e-9) & (xs <= x1 + 1e-9)
    # вне анода тока через грань нет: там изолятор, в окно попадают только узлы анода
    Jl = np.where(inside, (w * Ii).sum(1) / np.maximum((w * Ai).sum(1), 1e-300), 0.0)
    return xs, Jl, float(Ii.sum())
