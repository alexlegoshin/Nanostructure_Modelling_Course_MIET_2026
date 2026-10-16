# -*- coding: utf-8 -*-
"""Картинки по результатам питоновского расчёта — в том же стиле, что и ISE-овские."""

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
               elev=16, azim=-64, width=348, height=276, zoom=1.25):
    """Плоскость сечения внутри каркаса прибора — как у ise3d, но из наших полей."""
    u, w, F = cut_plane(z, kind, value)
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
