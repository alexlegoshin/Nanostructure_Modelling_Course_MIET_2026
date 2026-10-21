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


# ------------------------------------------- |J| вдоль верхней границы сечения, как у эталона
# Эталон строит модуль полного вектора плотности тока на линии z = LZ, y = 1.5:
# под анодом это ток в контакт, вне анода — ток вдоль поверхности. Поэтому здесь
# считается именно |J|, а не только ток через контакт.

def _sg(psi_a, psi_b, n_a, n_b, p_a, p_b, Nt, h):
    """Поток Шарфеттера-Гуммеля по ребру a -> b (как в dd3d), А/см2, компонента вдоль ребра."""
    import dd3d
    d = (psi_a - psi_b) / dd3d.VT
    E = (psi_a - psi_b) / h
    mn = dd3d.mu_field(dd3d.mu_doping(Nt, "n"), E, "n")
    mp = dd3d.mu_field(dd3d.mu_doping(Nt, "p"), E, "p")
    Jn = Q * mn * dd3d.VT / h * (n_b * dd3d.bern(-d) - n_a * dd3d.bern(d))
    Jp = -Q * mp * dd3d.VT / h * (p_b * dd3d.bern(d) - p_a * dd3d.bern(-d))
    return Jn + Jp


def j_top_abs(path_npz, y=1.5):
    """Самописный решатель: |J| в узлах верхней грани на линии y = 1.5.
    Компоненты — из потоков по рёбрам вдоль x, y (по поверхности) и z (вниз), средние по узлу."""
    z = np.load(path_npz)
    psi, n, p, C = z["psi"], z["n"], z["p"], z["C"]
    x, yy, zz = z["x"], z["y"], z["z"]
    j = int(np.argmin(np.abs(yy - y * 1e-4))); k = len(zz) - 1

    def along(i0, i1, axis_h):
        Nt = 0.5 * (np.abs(C[i0]) + np.abs(C[i1]))
        return _sg(psi[i0], psi[i1], n[i0], n[i1], p[i0], p[i1], Nt, axis_h)

    nx = len(x)
    jx = np.zeros(nx); jy = np.zeros(nx); jz = np.zeros(nx)
    ex = np.array([along((i, j, k), (i + 1, j, k), x[i + 1] - x[i]) for i in range(nx - 1)])
    jx[1:-1] = 0.5 * (ex[1:] + ex[:-1]); jx[0], jx[-1] = ex[0], ex[-1]
    for i in range(nx):
        a = along((i, j - 1, k), (i, j, k), yy[j] - yy[j - 1])
        b = along((i, j, k), (i, j + 1, k), yy[j + 1] - yy[j])
        jy[i] = 0.5 * (a + b)
        jz[i] = along((i, j, k - 1), (i, j, k), zz[k] - zz[k - 1])
    return x * 1e4, np.sqrt(jx ** 2 + jy ** 2 + jz ** 2)


def devsim_j_vector(zd, nodes=None):
    """DEVSIM: вектор J в узлах — наименьшие квадраты по плотностям тока на прилегающих рёбрах
    (edge_j из run_ise.py; рёбра с нулевой площадью грани тока не несут и пропускаются)."""
    r = np.stack([zd["x"], zd["y"], zd["z"]], 1)
    a, b, je = zd["edge_a"], zd["edge_b"], zd["edge_j"]
    ok = ~np.isnan(je); a, b, je = a[ok], b[ok], je[ok]
    t = r[b] - r[a]; t /= np.linalg.norm(t, axis=1)[:, None]
    N = len(r); AtA = np.zeros((N, 3, 3)); Atb = np.zeros((N, 3))
    for idx in (a, b):                                  # проекция J на ребро известна в обоих концах
        np.add.at(AtA, idx, t[:, :, None] * t[:, None, :])
        np.add.at(Atb, idx, t * je[:, None])
    sel = np.arange(N) if nodes is None else np.asarray(nodes)
    J = np.full((len(sel), 3), np.nan)
    good = np.linalg.matrix_rank(AtA[sel]) == 3
    J[good] = np.linalg.solve(AtA[sel][good], Atb[sel][good][..., None])[..., 0]
    return J


def devsim_j_top_abs(path_npz, LZ=0.8, y=1.5):
    """DEVSIM: |J| в узлах верхней грани на линии y = 1.5 (сетка ISE — узлы на этой линии есть)."""
    zd = np.load(path_npz)
    r = np.stack([zd["x"], zd["y"], zd["z"]], 1) * 1e4
    sel = np.nonzero((np.abs(r[:, 2] - LZ) < 1e-6) & (np.abs(r[:, 1] - y) < 1e-6))[0]
    sel = sel[np.argsort(r[sel, 0])]
    J = devsim_j_vector(zd, sel)
    return r[sel, 0], np.linalg.norm(J, axis=1), J


# ------------------------------------------------ поля для сечений в шкале эталона
def j_abs_tensor(z):
    """Самописный решатель: |J| во всех узлах тензорной сетки (потоки по рёбрам x, y, z, средние по узлу)."""
    import dd3d
    psi, n, p, C = z["psi"], z["n"], z["p"], z["C"]
    axes = (z["x"], z["y"], z["z"])
    comps = []
    for ax in range(3):
        sl0 = [slice(None)] * 3; sl1 = [slice(None)] * 3
        sl0[ax] = slice(0, -1); sl1[ax] = slice(1, None)
        a, b = tuple(sl0), tuple(sl1)
        h = np.diff(axes[ax]).reshape([-1 if i == ax else 1 for i in range(3)])
        Nt = 0.5 * (np.abs(C[a]) + np.abs(C[b]))
        e = _sg(psi[a], psi[b], n[a], n[b], p[a], p[b], Nt, h)        # на рёбрах
        node = np.zeros_like(psi); cnt = np.zeros_like(psi)
        node[a] += e; cnt[a] += 1; node[b] += e; cnt[b] += 1
        comps.append(node / cnt)
    return np.sqrt(sum(c ** 2 for c in comps))


def cut_plane_field(z, F3, kind, value, fine=5):
    """Срез произвольного поля F3[x, y, z] тензорной сетки (как cut_plane, но не только заряд)."""
    if kind == "y":
        j = int(np.argmin(np.abs(z["y"] - value * 1e-4)))
        u, w, F = z["x"] * 1e4, z["z"] * 1e4, F3[:, j, :]
    else:
        j = int(np.argmin(np.abs(z["x"] - value * 1e-4)))
        u, w, F = z["y"] * 1e4, z["z"] * 1e4, F3[j, :, :]
    if fine > 1:
        from scipy.interpolate import RegularGridInterpolator
        f = RegularGridInterpolator((u, w), F, method="linear")
        u2 = np.linspace(u[0], u[-1], len(u) * fine); w2 = np.linspace(w[0], w[-1], len(w) * fine)
        U, W = np.meshgrid(u2, w2, indexing="ij")
        F = f(np.stack([U.ravel(), W.ravel()], axis=1)).reshape(U.shape); u, w = u2, w2
    return u, w, F


def devsim_plane(zd, vals, kind, value, nu=120, nw=96):
    """DEVSIM: узловые значения vals на регулярную решётку плоскости (по тетраэдрам сетки)."""
    pts = np.stack([zd["x"], zd["y"], zd["z"]], axis=1) * 1e4
    u = np.linspace(pts[:, 0].min(), pts[:, 0].max(), nu) if kind == "y" else \
        np.linspace(pts[:, 1].min(), pts[:, 1].max(), nu)
    w = np.linspace(pts[:, 2].min(), pts[:, 2].max(), nw)
    U, W = np.meshgrid(u, w, indexing="ij")
    P = np.stack([U, np.full_like(U, value), W], -1) if kind == "y" else np.stack([np.full_like(U, value), U, W], -1)
    return u, w, tet_interp(zd, vals, P.reshape(-1, 3)).reshape(U.shape)
