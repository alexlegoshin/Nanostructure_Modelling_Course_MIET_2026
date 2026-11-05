# -*- coding: utf-8 -*-
"""Иллюстрации работы 5 из выгруженных результатов ISE — сам ISE не нужен.

    python3 Lab5_MESFET_mixed_mode/make_figures.py

Каждая позиция строится в размере, рамке и пределах осей своей эталонной иллюстрации
(reference/, Svisual): рамки сняты с эталонов по линиям сетки, графики —
ise_style.xy_svisual, карты — 30 полос палитры Svisual. Задания, которые ещё не
посчитаны, пропускаются.
"""
import os, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation, LinearTriInterpolator
import viz, dfise, sheet
import ise_style as ise

ISE = os.path.join(HERE, "ise") + "/"
REF = os.path.join(HERE, "reference") + "/"
OUT = os.path.join(HERE, "results", "ise") + "/"

# вариант 2
N01, A01, F1, UM2 = 8.0e17, 0.05, 9e3, 0.25
VG_FAMILY = (0.8, 0.0, -0.8, -1.6, -2.4)
VD_FAMILY = (0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)   # как в примере методических указаний; Svisual
                                                    # округляет подписи легенды до 0.2 и 0.8

S = ise.SVISUAL
# палитра карт Svisual: 30 полос, синий → голубой → зелёный → жёлтый → красный
_G = (34, 74, 121, 168, 210, 240, 254)
MAP = ([(0, g, 255) for g in _G] + [(0, 255, b) for b in (249, 227, 191, 145, 97, 53, 20, 2)] +
       [(r, 255, 0) for r in (2, 20, 53, 97, 145, 191, 227, 249)] + [(255, g, 0) for g in (254, 240, 210, 168, 121, 74, 34)])
MAP = [tuple(v / 255.0 for v in c) for c in MAP]

XY = {
    "z2_вах_IdVd": dict(size=(763, 655), frame=(70, 643, 38, 593), xlim=(0, 2), ylim=(0, 0.5), xstep=0.5,
                        ystep=0.1, title="IdVd Curves", xlabel="Vd (V)", ylabel="Id (A/mm)", fs=14),
    "z2_вах_IdVg": dict(size=(763, 655), frame=(70, 644, 38, 593), xlim=(-10, 2), ylim=(0, 0.5), xstep=5,
                        ystep=0.1, title="IdVg Curves", xlabel="Vg (V)", ylabel="Id (A/mm)", fs=14),
    "z3_сигналы_затвора": dict(size=(642, 673), frame=(77, 561, 38, 611), xlim=(0, 4e-3), ylim=None,
                               xstep=1e-3, ystep=0.5, title="Gate: Signals (Voltage)", xlabel="t (s)",
                               ylabel="Vg (V)", fs=14, first_on_top=True),
    "z3_низкочастотный_сигнал": dict(size=(642, 673), frame=(77, 516, 38, 611), xlim=(0, 4e-3),
                                     ylim=(-0.4, 0.4), xstep=1e-3, ystep=0.2,
                                     title="Gate: Low-frequency Signal (Voltage)", xlabel="t (s)",
                                     ylabel="Vg (V)", fs=14),
    "z3_ток_стока": dict(size=(642, 673), frame=(90, 523, 38, 611), xlim=(1e-7, 4e-3), ylim=None, xstep=1e-3,
                         ystep=0.005, title="Drain: Signal (Current)", xlabel="t (s)", ylabel="Id (A/mm)",
                         fs=14),
    "z4_АМ_сигнал": dict(size=(642, 673), frame=(77, 516, 38, 611), xlim=(0, 4e-3), ylim=None, xstep=1e-3,
                         ystep=0.2, title="Filter: Modulated Signal (Voltage)", xlabel="t (s)", ylabel="Vd (V)",
                         fs=14),
}
# карты: размер картинки и прямоугольник прибора (x 0…4, y 0…0.36 мкм) в пикселях
# карты: размер, рамка осей (л, п, в, н) и пиксели засечек x = 0, 4 мкм и y = 0, 0.3 мкм — с эталонов
MAPS = {"z1_легирование": ((851, 691), (87, 808, 34, 615), (97, 797, 69, 489)),
        "z1_сетка": ((851, 691), (87, 808, 34, 615), (97, 797, 69, 489)),
        "z2_плотность_тока": ((851, 691), (87, 808, 34, 615), (93, 801, 65, 491))}
OUTLINE = [(0, 0), (0.8, 0), (0.8, 0.04), (1.6, 0.04), (1.6, 0.08), (2.4, 0.08), (2.4, 0.04), (3.2, 0.04),
           (3.2, 0), (4, 0), (4, 0.36), (0, 0.36), (0, 0)]
CONTACTS = [((0, 0), (0.4, 0)), ((1.75, 0.08), (2.25, 0.08)), ((3.6, 0), (4, 0))]
NAMES = [("Задание 1. Легирование", "z1_легирование"), ("Задание 1. Сетка", "z1_сетка"),
         ("Задание 2. Плотность тока и линии тока, Vg = 0.8 В, Vd = 2 В", "z2_плотность_тока"),
         ("Задание 2. Семейство Id(Vd)", "z2_вах_IdVd"), ("Задание 2. Семейство Id(Vg)", "z2_вах_IdVg"),
         ("Задание 3. Сигналы на затворе", "z3_сигналы_затвора"),
         ("Задание 3. Низкочастотный сигнал", "z3_низкочастотный_сигнал"),
         ("Задание 3. Ток стока", "z3_ток_стока"), ("Задание 4. Амплитудно-модулированный сигнал", "z4_АМ_сигнал")]


def tag_vg(v):
    return ("p" if v >= 0 else "m") + "%02d" % round(abs(v) * 10)


def plt_or_none(path):
    return viz.read_plt(path) if os.path.exists(path) else None


def idvg(T2, vd):
    """Id(Vg) при заданном Vd. Прямой проход Vg = −10 → 2 В при Vd = 2 В останавливается
    на Vg ≈ −6.7 В (Ньютон не сходится при любом шаге); для этой кривой дополнительно
    посчитаны проходы от открытого канала (Vg = 0) вверх до 2 В и вниз до −10 В
    (t_vd2b_des.cmd), и кривая собирается из них: стационарные решения от направления
    прохода не зависят, на общих участках проходы совпадают."""
    c = plt_or_none(T2 + "Vd_%03d_t_des.plt" % round(vd * 100))
    V, I = (np.asarray(c["gate OuterVoltage"]), np.asarray(c["drain TotalCurrent"])) if c is not None else ([], [])
    up, dn = plt_or_none(T2 + "Vd2up_t_des.plt"), plt_or_none(T2 + "Vd2dn_t_des.plt")
    if vd == 2.0 and up is not None and dn is not None:
        g = lambda d, k: np.asarray(d["%s OuterVoltage" % k] if k == "gate" else d["drain TotalCurrent"])
        Vu, Iu = g(up, "gate"), g(up, "I"); Vn, In = g(dn, "gate"), g(dn, "I")
        Vn, In = Vn[::-1], In[::-1]
        low = np.asarray(V) < Vn.min() - 1e-9                  # недостающий низ — из прямого прохода
        V = np.concatenate([np.asarray(V)[low], Vn, Vu]); I = np.concatenate([np.asarray(I)[low], In, Iu])
    return (np.asarray(V), np.asarray(I)) if len(V) else None


def threshold(V, I):
    """Порог по методике методических указаний (как в работе 4): x0 — максимум второй
    производной Id(Vg) в «пятке» ВАХ, касательная в этой точке пересекает ось Vg в VT.
    Здесь x0 и VT близки, и, как допускают указания, порогом берётся x0.
    Возвращает (x0, VT по касательной)."""
    o = np.argsort(V); V, I = V[o], I[o]
    m = V < V[np.argmax(I)] - 0.5                     # участок до максимума тока
    V, I = V[m], I[m]
    d1 = np.gradient(I, V); d2 = np.gradient(d1, V)
    i0 = int(np.argmax(d2))
    return V[i0], V[i0] - I[i0] / d1[i0]


def _device_map(path, size, box, ticks, grid, F, mesh=False, stream=None, title="", outline=True, depletion=None):
    """Карта поля в стиле Svisual: 30 полос, оси вынесены за прибор, как на эталоне."""
    W, H = size
    l, r, t, b = box
    x0, x4, y0, y3 = ticks
    kx, ky = (x4 - x0) / 4.0, (y3 - y0) / 0.3                      # пикселей на мкм
    fig = plt.figure(figsize=((W + 0.1) / 100.0, (H + 0.1) / 100.0), dpi=100)
    ax = fig.add_axes([l / W, 1 - b / H, (r - l) / W, (b - t) / H])
    v = grid["vertices"]
    tri = Triangulation(v[:, 0], v[:, 1], dfise.triangles(grid))
    lv = np.linspace(np.nanmin(F), np.nanmax(F), len(MAP) + 1)
    from matplotlib.collections import LineCollection
    with matplotlib.rc_context({"lines.antialiased": False, "patch.antialiased": False}):
        ax.tricontourf(tri, F, levels=lv, colors=MAP, extend="both", antialiased=False)
        if mesh:                                   # каждое ребро ячейки — один раз, без диагоналей
            edges = set()
            for _, ring in grid["elements"]:
                for i in range(len(ring)):
                    a_, b_ = ring[i], ring[(i + 1) % len(ring)]
                    edges.add((min(a_, b_), max(a_, b_)))
            ax.add_collection(LineCollection([v[list(e)] for e in edges], colors="k", linewidths=1 * ise.PX))
        if stream is not None:
            X, Y, U, Vv, starts = stream
            sp = ax.streamplot(X, Y, U, Vv, start_points=starts, color="k", linewidth=0.5 * ise.PX,
                               arrowstyle="-", integration_direction="both", density=10, broken_streamlines=False)
            sp.lines.set_antialiased(False)
        if depletion is not None:
            ax.tricontour(tri, depletion, levels=[0.2], colors="w", linewidths=1.5 * ise.PX)
        if outline:
            ax.plot(*zip(*OUTLINE), color="k", lw=1 * ise.PX)
            for c in CONTACTS:
                ax.plot(*zip(*c), color=(1, 0, 1), lw=2 * ise.PX, solid_capstyle="butt")
    ax.set_xlim((l - x0) / kx, (r - x0) / kx); ax.set_ylim((b - y0) / ky, (t - y0) / ky)
    ax.set_xticks([0, 1, 2, 3, 4]); ax.set_yticks([0, 0.1, 0.2, 0.3])
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda q, _: "%g" % q))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda q, _: "%g" % q))
    ax.tick_params(direction="out", length=5 * ise.PX, width=1 * ise.PX, labelsize=10, pad=2)
    for tl in ax.get_xticklabels() + ax.get_yticklabels():
        tl.set_fontfamily(ise.HELV); tl.set_fontweight("bold")
    for k, sp in ax.spines.items():
        sp.set_visible(k in ("left", "bottom")); sp.set_linewidth(1 * ise.PX)
    fig.text((x0 + x4) / 2 / W, 1 - 655 / H, "X", ha="center", va="center", fontfamily=ise.HELV,
             fontweight="bold", fontsize=14)
    fig.text(45 / W, 1 - (y0 + 0.36 * ky + y0) / 2 / H, "Y", ha="center", va="center", fontfamily=ise.HELV,
             fontweight="bold", fontsize=14)
    if title:
        fig.text((x0 + x4) / 2 / W, 1 - 12 / H, title, ha="center", va="center", fontfamily="DejaVu Sans", fontsize=5)
    fig.savefig(path, dpi=100, facecolor="white")
    plt.close(fig)


def figures():
    os.makedirs(OUT, exist_ok=True)
    made = []
    T2 = ISE + "task2/"
    if os.path.exists(T2 + "t_msh.grd"):
        g = dfise.read_grid(T2 + "t_msh.grd"); d = dfise.read_dataset(T2 + "t_msh.dat", g)
        dop = d["DopingConcentration"]
        # как у эталонов: легирование — в линейной шкале, под сеткой — в логарифмической
        _device_map(OUT + "z1_легирование.png", *MAPS["z1_легирование"], g, dop, title="t_msh")
        _device_map(OUT + "z1_сетка.png", *MAPS["z1_сетка"], g, np.log10(np.maximum(dop, 1e10)), mesh=True,
                    title="t_msh", outline=False)
        made += ["z1_легирование", "z1_сетка"]
    if os.path.exists(T2 + "t_des.dat"):
        g = dfise.read_grid(T2 + "t_msh.grd"); d = dfise.read_dataset(T2 + "t_des.dat", g)
        J = np.asarray(d["TotalCurrentDensity-Vector"])
        Jm = np.linalg.norm(J, axis=1)                     # как у эталона: |J| в линейной шкале
        v = g["vertices"]; tri = Triangulation(v[:, 0], v[:, 1], dfise.triangles(g))
        X, Y = np.meshgrid(np.linspace(0, 4, 400), np.linspace(0, 0.36, 300))
        U = LinearTriInterpolator(tri, J[:, 0])(X, Y).filled(0); Vv = LinearTriInterpolator(tri, J[:, 1])(X, Y).filled(0)
        starts = np.array([[x, 0.003] for x in (0.36, 0.39, 0.42, 0.45)])   # линии тока — от края истока
        # граница обеднённой области (белая линия эталона): электронов в 5 раз меньше, чем доноров
        dep = np.asarray(d["eDensity"]) / np.maximum(np.asarray(d["DonorConcentration"]), 1.0)
        dep[v[:, 1] > 0.15] = 1.0                          # только над каналом: глубже легирование 1e14
        _device_map(OUT + "z2_плотность_тока.png", *MAPS["z2_плотность_тока"], g, Jm, stream=(X, Y, U, Vv, starts),
                    title="t_des(t_msh)", depletion=dep)
        made.append("z2_плотность_тока")
    s = [plt_or_none(T2 + "Vg_%s_t_des.plt" % tag_vg(v)) for v in VG_FAMILY]
    if all(c is not None for c in s):
        cols = ("maroon", "green", "blue", "red", "black")
        ise.xy_svisual([(np.asarray(c["drain OuterVoltage"]), np.asarray(c["drain TotalCurrent"]), S[k],
                         "Vg = %.1f(V)" % v) for c, k, v in zip(s, cols, VG_FAMILY)],
                       OUT + "z2_вах_IdVd.png", **XY["z2_вах_IdVd"])
        made.append("z2_вах_IdVd")
    s = [idvg(T2, v) for v in VD_FAMILY]
    if any(c is not None for c in s):
        cols = ("cyan", "magenta", "maroon", "green", "blue", "red", "black")
        ise.xy_svisual([(c[0], c[1], S[k], "Vd = %.1f (V)" % v) for c, k, v in zip(s, cols, VD_FAMILY) if c is not None],
                       OUT + "z2_вах_IdVg.png", **XY["z2_вах_IdVg"])
        made.append("z2_вах_IdVg")
    n = plt_or_none(ISE + "task3/New_nodes.plt"); f = plt_or_none(ISE + "task3/New_fet_des.plt")
    if n is not None:
        t = np.asarray(n["time"])
        ise.xy_svisual([(t, np.asarray(n["v(n3)"]), S["red"], "V(n3)"), (t, np.asarray(n["v(n2)"]), S["blue"], "V(n2)")],
                       OUT + "z3_сигналы_затвора.png", **XY["z3_сигналы_затвора"])
        ise.xy_svisual([(t, np.asarray(n["v(n3)"]) - np.asarray(n["v(n2)"]), S["red"], "V(n3)-V(n2))")],
                       OUT + "z3_низкочастотный_сигнал.png", **XY["z3_низкочастотный_сигнал"])
        made += ["z3_сигналы_затвора", "z3_низкочастотный_сигнал"]
    if f is not None:
        ise.xy_svisual([(np.asarray(f["time"]), np.abs(np.asarray(f["drain TotalCurrent"])), S["red"], "Vd = 1.0 (V)")],
                       OUT + "z3_ток_стока.png", **XY["z3_ток_стока"])
        made.append("z3_ток_стока")
    n = plt_or_none(ISE + "task4/New_nodes.plt")
    if n is not None:
        ise.xy_svisual([(np.asarray(n["time"]), np.asarray(n["v(n4)"]) - np.asarray(n["v(n6)"]), S["blue"], "V(n4)-V(n6))")],
                       OUT + "z4_АМ_сигнал.png", **XY["z4_АМ_сигнал"])
        made.append("z4_АМ_сигнал")
    return made


def comparison_grid():
    rows = [(lab.split(". ", 1)[1], [REF + f + ".png", OUT + f + ".png"]) for lab, f in NAMES]
    sheet.grid(rows, ["эталон", "ISE"], os.path.join(HERE, "results", "сравнение.png"))


if __name__ == "__main__":
    print("построено:", figures())
    comparison_grid()
