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
VD_FAMILY = (0.1, 0.2, 0.5, 0.8, 1.0, 1.5, 2.0)

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
                               ylabel="Vg (V)", legend_x=565, fs=14),
    "z3_низкочастотный_сигнал": dict(size=(642, 673), frame=(77, 516, 38, 611), xlim=(0, 4e-3),
                                     ylim=(-0.4, 0.4), xstep=1e-3, ystep=0.2,
                                     title="Gate: Low-frequency Signal (Voltage)", xlabel="t (s)",
                                     ylabel="Vg (V)", legend_x=520, fs=14),
    "z3_ток_стока": dict(size=(642, 673), frame=(90, 523, 38, 611), xlim=(0, 4e-3), ylim=None, xstep=1e-3,
                         ystep=0.005, title="Drain: Signal (Current)", xlabel="t (s)", ylabel="Id (A/mm)",
                         legend_x=527, fs=14),
    "z4_АМ_сигнал": dict(size=(642, 673), frame=(77, 516, 38, 611), xlim=(0, 4e-3), ylim=None, xstep=1e-3,
                         ystep=0.2, title="Filter: Modulated Signal (Voltage)", xlabel="t (s)", ylabel="Vd (V)",
                         legend_x=520, fs=14),
}
# карты: размер картинки и прямоугольник прибора (x 0…4, y 0…0.36 мкм) в пикселях
MAPS = {"z1_легирование": ((851, 691), (98, 796, 68, 572)), "z1_сетка": ((851, 691), (98, 796, 68, 572)),
        "z2_плотность_тока": ((851, 691), (93, 800, 64, 575))}
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


def _device_map(path, size, box, grid, F, mesh=False, stream=None, levels=None):
    W, H = size
    l, r, t, b = box
    fig = plt.figure(figsize=((W + 0.1) / 100.0, (H + 0.1) / 100.0), dpi=100)
    ax = fig.add_axes([l / W, 1 - b / H, (r - l) / W, (b - t) / H])
    v = grid["vertices"]
    tri = Triangulation(v[:, 0], v[:, 1], dfise.triangles(grid))
    lv = levels if levels is not None else np.linspace(np.nanmin(F), np.nanmax(F), len(MAP) + 1)
    with matplotlib.rc_context({"lines.antialiased": False, "patch.antialiased": False}):
        ax.tricontourf(tri, F, levels=lv, colors=MAP, extend="both", antialiased=False)
        if mesh:
            ax.triplot(tri, color="k", lw=0.5 * ise.PX)
        if stream is not None:
            X, Y, U, Vv, starts = stream
            ax.streamplot(X, Y, U, Vv, start_points=starts, color="k", linewidth=1.0 * ise.PX,
                          arrowstyle="-", integration_direction="both", density=10, broken_streamlines=False)
    ax.set_xlim(0, 4); ax.set_ylim(0.36, 0)
    ax.set_xticks([0, 1, 2, 3, 4]); ax.set_yticks([0, 0.1, 0.2, 0.3])
    ax.tick_params(direction="out", length=4 * ise.PX, labelsize=9)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.text((l + r) / 2 / W, 1 - (b + 50) / H, "X", ha="center", fontfamily=ise.HELV, fontweight="bold", fontsize=12)
    fig.text((l - 30) / W, 1 - (t + b) / 2 / H, "Y", ha="center", va="center", fontfamily=ise.HELV,
             fontweight="bold", fontsize=12)
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
        _device_map(OUT + "z1_легирование.png", *MAPS["z1_легирование"], g, dop)
        _device_map(OUT + "z1_сетка.png", *MAPS["z1_сетка"], g, np.log10(np.maximum(dop, 1e10)), mesh=True)
        made += ["z1_легирование", "z1_сетка"]
    if os.path.exists(T2 + "t_des.dat"):
        g = dfise.read_grid(T2 + "t_msh.grd"); d = dfise.read_dataset(T2 + "t_des.dat", g)
        J = np.asarray(d["TotalCurrentDensity-Vector"])
        Jm = np.log10(np.maximum(np.linalg.norm(J, axis=1), 1.0))
        v = g["vertices"]; tri = Triangulation(v[:, 0], v[:, 1], dfise.triangles(g))
        X, Y = np.meshgrid(np.linspace(0, 4, 400), np.linspace(0, 0.36, 300))
        U = LinearTriInterpolator(tri, J[:, 0])(X, Y).filled(0); Vv = LinearTriInterpolator(tri, J[:, 1])(X, Y).filled(0)
        starts = np.array([[0.2, y] for y in (0.02, 0.05, 0.08, 0.11, 0.14)])
        _device_map(OUT + "z2_плотность_тока.png", *MAPS["z2_плотность_тока"], g, Jm, stream=(X, Y, U, Vv, starts))
        made.append("z2_плотность_тока")
    s = [plt_or_none(T2 + "Vg_%s_t_des.plt" % tag_vg(v)) for v in VG_FAMILY]
    if all(c is not None for c in s):
        cols = ("maroon", "green", "blue", "red", "black")
        ise.xy_svisual([(np.asarray(c["drain OuterVoltage"]), np.asarray(c["drain TotalCurrent"]), S[k],
                         "Vg = %.1f(V)" % v) for c, k, v in zip(s, cols, VG_FAMILY)],
                       OUT + "z2_вах_IdVd.png", **XY["z2_вах_IdVd"])
        made.append("z2_вах_IdVd")
    s = [plt_or_none(T2 + "Vd_%03d_t_des.plt" % round(v * 100)) for v in VD_FAMILY]
    if any(c is not None for c in s):
        cols = ("cyan", "magenta", "maroon", "green", "blue", "red", "black")
        ise.xy_svisual([(np.asarray(c["gate OuterVoltage"]), np.asarray(c["drain TotalCurrent"]), S[k],
                         "Vd = %.1f (V)" % v) for c, k, v in zip(s, cols, VD_FAMILY) if c is not None],
                       OUT + "z2_вах_IdVg.png", **XY["z2_вах_IdVg"])
        made.append("z2_вах_IdVg")
    n = plt_or_none(ISE + "task3/New_nodes.plt"); f = plt_or_none(ISE + "task3/New_fet_des.plt")
    if n is not None:
        t = np.asarray(n["time"])
        ise.xy_svisual([(t, np.asarray(n["n3"]), S["red"], "V(n3)"), (t, np.asarray(n["n2"]), S["blue"], "V(n2)")],
                       OUT + "z3_сигналы_затвора.png", **XY["z3_сигналы_затвора"])
        ise.xy_svisual([(t, np.asarray(n["n3"]) - np.asarray(n["n2"]), S["red"], "V(n3)-V(n2))")],
                       OUT + "z3_низкочастотный_сигнал.png", **XY["z3_низкочастотный_сигнал"])
        made += ["z3_сигналы_затвора", "z3_низкочастотный_сигнал"]
    if f is not None:
        ise.xy_svisual([(np.asarray(f["time"]), np.abs(np.asarray(f["drain TotalCurrent"])), S["red"], "Vd = 1.0 (V)")],
                       OUT + "z3_ток_стока.png", **XY["z3_ток_стока"])
        made.append("z3_ток_стока")
    n = plt_or_none(ISE + "task4/New_nodes.plt")
    if n is not None:
        ise.xy_svisual([(np.asarray(n["time"]), np.asarray(n["n4"]) - np.asarray(n["n6"]), S["blue"], "V(n4)-V(n6))")],
                       OUT + "z4_АМ_сигнал.png", **XY["z4_АМ_сигнал"])
        made.append("z4_АМ_сигнал")
    return made


def comparison_grid():
    rows = [(lab.split(". ", 1)[1], [REF + f + ".png", OUT + f + ".png"]) for lab, f in NAMES]
    sheet.grid(rows, ["эталон", "ISE"], os.path.join(HERE, "results", "сравнение.png"))


if __name__ == "__main__":
    print("построено:", figures())
    comparison_grid()
