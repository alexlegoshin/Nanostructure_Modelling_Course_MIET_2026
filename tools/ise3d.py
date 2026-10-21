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


def _colors_on_grid(grid, vals, nu=160, nv=96, lo=None, hi=None):
    """Поле с треугольной сетки на регулярную, уже в виде цветов полос.
    lo, hi — границы шкалы (в ареасинусе); по умолчанию — min..max самого сечения."""
    v = grid["vertices"]
    tri = Triangulation(v[:, 0], v[:, 1], dfise.triangles(grid))
    f = LinearTriInterpolator(tri, ise._t(vals))       # интерполируем преобразованное
    u = np.linspace(v[:, 0].min(), v[:, 0].max(), nu)
    w = np.linspace(v[:, 1].min(), v[:, 1].max(), nv)
    U, W = np.meshgrid(u, w)
    T = f(U, W)
    lo = float(ise._t(vals).min()) if lo is None else lo
    hi = float(ise._t(vals).max()) if hi is None else hi
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


# ============================================================ ракурс эталона
# Эталоны лабы 3 нарисованы в перспективе, и у каждой картинки своя камера.
# Камера подгоняется по самой эталонной картинке: силуэт коробки даёт начальное
# приближение (DLT по шести углам), затем фокус, поворот и положение уточняются
# так, чтобы рёбра коробки и контакты легли на чёрные и пурпурные линии эталона.
# Ориентация, видимая на эталонах: впереди грань x = LX, справа торец y = LY, сверху z = LZ.

from PIL import Image
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scipy.ndimage import distance_transform_edt, map_coordinates, binary_erosion
from scipy.optimize import least_squares
from matplotlib.collections import PolyCollection, LineCollection

BLUE_REF, RED_REF, JUNC_REF = (0, 42 / 255, 1.0), (1.0, 4 / 255, 0), (153 / 255, 0, 0)


def _ref_masks(png):
    a = np.array(Image.open(png).convert("RGB")).astype(int)
    white = a.sum(2) >= 750
    gray = (np.abs(a[..., 0] - a[..., 1]) < 6) & (np.abs(a[..., 1] - a[..., 2]) < 6) \
        & (a[..., 0] > 150) & (a[..., 0] < 250)
    obj = ~white & ~gray
    black = a.sum(2) < 60
    mag = (a[..., 0] > 200) & (a[..., 1] < 60) & (a[..., 2] > 200)
    edge = obj & ~binary_erosion(obj)
    return obj, {k: distance_transform_edt(~m) for k, m in
                 (("black", black), ("mag", mag), ("edge", edge))}, a.shape[1], a.shape[0]


def _hexagon(obj):
    ys, xs = np.nonzero(obj)
    pts = np.c_[xs, ys].astype(float)
    P = pts[ConvexHull(pts).vertices]
    while len(P) > 6:                                     # оставить 6 главных вершин
        n = len(P)
        ar = [abs((P[i][0] - P[i - 1][0]) * (P[(i + 1) % n][1] - P[i - 1][1])
                  - (P[i][1] - P[i - 1][1]) * (P[(i + 1) % n][0] - P[i - 1][0])) for i in range(n)]
        P = np.delete(P, int(np.argmin(ar)), 0)
    iT, iF = int(np.argmin(P[:, 1])), int(np.argmax(P[:, 1]))
    rest = sorted([P[i] for i in range(6) if i not in (iT, iF)], key=lambda p: p[0])
    Lt, Lb = sorted(rest[:2], key=lambda p: p[1]); Rt, Rb = sorted(rest[2:], key=lambda p: p[1])
    return {"Lt": Lt, "T": P[iT], "Rt": Rt, "Rb": Rb, "Fb": P[iF], "Lb": Lb}


def project(cam, X):
    """Точки (N, 3) в мкм -> пиксели (N, 2) по камере cam = (f, cx, cy, rx, ry, rz, tx, ty, tz)."""
    f, cx, cy = cam[:3]
    C = (Rotation.from_rotvec(cam[3:6]).as_matrix() @ np.asarray(X, float).T).T + cam[6:9]
    return np.c_[f * C[:, 0] / C[:, 2] + cx, f * C[:, 1] / C[:, 2] + cy]


def camera_center(cam):
    R = Rotation.from_rotvec(cam[3:6]).as_matrix()
    return -R.T @ np.asarray(cam[6:9])


def _box_segments(kind, LX, LY, LZ, anode):
    c = [(0, 0, 0), (LX, 0, 0), (LX, LY, 0), (0, LY, 0)]
    t = [(x, y, LZ) for x, y, _ in c]
    x0, y0, x1, y1 = anode
    an = [(x0, y0, LZ), (x1, y0, LZ), (x1, y1, LZ), (x0, y1, LZ)]
    S = []
    if kind == "cut":
        S += [(t[i], t[(i + 1) % 4], "black") for i in range(4)] + [(c[i], t[i], "black") for i in range(4)]
        S += [(c[i], c[(i + 1) % 4], "mag") for i in range(4)]
    else:
        Lt, T, Rt, Rb, Fb, Lb = (LX, 0, LZ), (0, 0, LZ), (0, LY, LZ), (0, LY, 0), (LX, LY, 0), (LX, 0, 0)
        S += [(a, b, "edge") for a, b in ((Lt, T), (T, Rt), (Rt, Rb), (Rb, Fb), (Fb, Lb), (Lb, Lt))]
    S += [(an[i], an[(i + 1) % 4], "mag") for i in range(4)]
    return S


def fit_camera(ref_png, kind, anode, LX=1.0, LY=3.0, LZ=0.8):
    """Камера эталонной картинки. kind: 'cut' (каркас) или 'structure' (сплошная коробка).
    Возвращает (cam, (W, H), средний промах рёбер в пикселях)."""
    obj, D, W, H = _ref_masks(ref_png)
    hx = _hexagon(obj)
    c3 = {"Lt": (LX, 0, LZ), "T": (0, 0, LZ), "Rt": (0, LY, LZ), "Rb": (0, LY, 0), "Fb": (LX, LY, 0), "Lb": (LX, 0, 0)}
    A = []
    for k in hx:                                          # DLT по шести углам силуэта
        (x, y, z), (u, v) = c3[k], hx[k]
        A.append([x, y, z, 1, 0, 0, 0, 0, -u * x, -u * y, -u * z, -u])
        A.append([0, 0, 0, 0, x, y, z, 1, -v * x, -v * y, -v * z, -v])
    P = np.linalg.svd(np.array(A))[2][-1].reshape(3, 4)
    from scipy.linalg import rq
    K, R = rq(P[:, :3]); Dg = np.diag(np.sign(np.diag(K))); K, R = K @ Dg, Dg @ R
    t = np.linalg.solve(K, P[:, 3])
    if np.linalg.det(R) < 0:
        R, t = -R, -t
    K = K / K[2, 2]
    cam0 = np.r_[0.5 * (K[0, 0] + K[1, 1]), K[0, 2], K[1, 2], Rotation.from_matrix(R).as_rotvec(), t]
    segs = _box_segments(kind, LX, LY, LZ, anode)
    s = np.linspace(0, 1, 40)[:, None]

    def res(cam):
        out = []
        for a, b, m in segs:
            uv = project(cam, np.array(a) + s * (np.array(b) - np.array(a)))
            out.append(map_coordinates(D[m], [uv[:, 1], uv[:, 0]], order=1, mode="nearest"))
        return np.concatenate(out)
    r = least_squares(res, cam0, loss="soft_l1", f_scale=2.0)
    return r.x, (W, H), float(np.mean(np.abs(res(r.x))))


def _rgb(c):
    return tuple(int(round(v * 255)) for v in c[:3])


def structure_ref(path, verts, tris, dop, LX, LY, LZ, anode, cam, size):
    """Структура в ракурсе эталона: видимые грани поверхности, синяя p- и красная
    n-область, чёрная сетка в 1 пиксель (как у X11 — без сглаживания), линия перехода
    и контакты. verts — вершины (мкм), tris — треугольники поверхности, dop — легирование."""
    from PIL import ImageDraw
    V = np.asarray(verts, float); T = np.asarray(tris)
    eye = camera_center(cam)
    c = V[T].mean(1)
    nrm = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    box_c = np.array([LX / 2, LY / 2, LZ / 2])
    nrm *= np.sign(((c - box_c) * nrm).sum(1))[:, None]   # наружу
    vis = ((eye - c) * nrm).sum(1) > 0
    uv = project(cam, V)
    img = Image.new("RGB", size, "white"); d = ImageDraw.Draw(img)
    sgn = np.asarray(dop)[T[vis]].mean(1)
    tri2 = uv[T[vis]]
    for t, sg in zip(tri2, sgn):                          # сначала заливка, потом все рёбра
        d.polygon([tuple(p) for p in t], fill=_rgb(BLUE_REF if sg < 0 else RED_REF))
    for t in tri2:
        d.line([tuple(p) for p in t] + [tuple(t[0])], fill=(0, 0, 0), width=1)
    zj = LZ / 2                                           # линия перехода по видимым боковым граням
    for a, b, n in (((LX, 0, zj), (LX, LY, zj), (1, 0, 0)), ((0, 0, zj), (0, LY, zj), (-1, 0, 0)),
                    ((0, 0, zj), (LX, 0, zj), (0, -1, 0)), ((0, LY, zj), (LX, LY, zj), (0, 1, 0))):
        mid = (np.array(a) + np.array(b)) / 2
        if ((eye - mid) * np.array(n)).sum() > 0:
            d.line([tuple(p) for p in project(cam, [a, b])], fill=_rgb(JUNC_REF), width=1)
    x0, y0, x1, y1 = anode                                # анод сверху, катод — видимые нижние рёбра
    d.line([tuple(p) for p in project(cam, [(x0, y0, LZ), (x1, y0, LZ), (x1, y1, LZ), (x0, y1, LZ), (x0, y0, LZ)])],
           fill=_rgb(MAGENTA), width=2)
    d.line([tuple(p) for p in project(cam, [(LX, 0, 0), (LX, LY, 0), (0, LY, 0)])], fill=_rgb(MAGENTA), width=2)
    img.save(path)
    return path


def bands_rgba(F, lo=None, hi=None, transform=True):
    """Поле -> цвета 31 полосы, по умолчанию в шкале ареасинуса (как у picasso).
    lo, hi — границы шкалы в преобразованных величинах (для общей шкалы на весь прибор);
    transform=False — поле уже в нужной шкале (например, lg|J|)."""
    t = ise._t(F) if transform else np.asarray(F, float)
    lo = float(np.nanmin(t)) if lo is None else lo
    hi = float(np.nanmax(t)) if hi is None else hi
    if hi <= lo:
        hi = lo + 1.0
    k = np.clip(((np.nan_to_num(t, nan=lo) - lo) / (hi - lo) * NB).astype(int), 0, NB - 1)
    rgba = np.zeros(k.shape + (4,)); rgba[..., 3] = 1.0
    for i in range(NB):
        rgba[k == i, :3] = ise.RGB[i]
    rgba[np.isnan(t), 3] = 0.0
    return rgba


def cut_ref(path, P3, rgba, kind, value, LX, LY, LZ, anode, cam, size):
    """Сечение в ракурсе эталона. P3 — точки плоскости (nw, nu, 3) в мкм, rgba — их цвета.
    Рёбра каркаса и контакты за плоскостью рисуются под ней, перед плоскостью — поверх."""
    from PIL import ImageDraw
    eye = camera_center(cam)
    n = np.array([0, 1.0, 0]) if kind == "y" else np.array([1.0, 0, 0])
    p0 = n * value
    side_eye = np.sign(((eye - p0) * n).sum())
    img = Image.new("RGB", size, "white"); d = ImageDraw.Draw(img)
    s = np.linspace(0, 1, 301)[:, None]
    lines = []
    for a, b, m in _box_segments("cut", LX, LY, LZ, anode):
        X = np.array(a) + s * (np.array(b) - np.array(a))
        behind = np.sign(((X - p0) * n).sum(1)) == -side_eye
        lines.append((project(cam, X), behind, (0, 0, 0) if m == "black" else _rgb(MAGENTA)))

    def draw_lines(flag):
        for p, behind, col in lines:
            sel = behind == flag
            i = 0
            while i < len(p):                             # непрерывные куски одной стороны
                if not sel[i]:
                    i += 1; continue
                j = i
                while j + 1 < len(p) and sel[j + 1]:
                    j += 1
                if j > i:
                    d.line([tuple(q) for q in p[i:j + 1]], fill=col, width=2)
                i = j + 1
    draw_lines(True)                                      # за плоскостью
    uv = project(cam, P3.reshape(-1, 3)).reshape(P3.shape[:2] + (2,))
    for i in range(P3.shape[0] - 1):
        for j in range(P3.shape[1] - 1):
            if rgba[i, j, 3] > 0:
                d.polygon([tuple(uv[i, j]), tuple(uv[i + 1, j]), tuple(uv[i + 1, j + 1]), tuple(uv[i, j + 1])],
                          fill=_rgb(rgba[i, j]))
    draw_lines(False)                                     # перед плоскостью
    img.save(path)
    return path


def plane_from_ise_cut(grid, vals, kind, value, nu=160, nw=96, lo=None, hi=None):
    """Сечение ISE (dfisetools -cut) -> точки плоскости в координатах прибора и цвета.
    У сечений поперёк прибора первая координата сечения — это -x, вдоль — y."""
    U, W, rgba = _colors_on_grid(grid, vals, nu=nu, nv=nw, lo=lo, hi=hi)
    if kind == "y":
        P3 = np.stack([-U, np.full_like(U, value), W], -1)
    else:
        P3 = np.stack([np.full_like(U, value), U, W], -1)
    return P3, rgba
