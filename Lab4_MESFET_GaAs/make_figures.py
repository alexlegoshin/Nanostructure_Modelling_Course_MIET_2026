# -*- coding: utf-8 -*-
"""Иллюстрации работы 4 из выгруженных результатов ISE — сам ISE не нужен.

    python3 Lab4_MESFET_GaAs/make_figures.py

Каждый график строится в размере, рамке и пределах осей своей эталонной иллюстрации
(reference/): рамки и пределы сняты с эталонов по линиям сетки, стиль — inspect
(ise_style.xy_inspect). Задания, которые ещё не посчитаны, пропускаются.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

import numpy as np
import viz, sheet
import ise_style as ise

ISE = os.path.join(HERE, "ise") + "/"
REF = os.path.join(HERE, "reference") + "/"
OUT = os.path.join(HERE, "results", "ise") + "/"

# вариант 2
H4, N4, H_OPEN, H_CLOSED = 0.02, 3.0e17, 0.05, 0.01
H_SCAN = (0.05, 0.04, 0.03, 0.02, 0.01, 0.0)
VG_OPEN = (("p08", 0.8), ("00", 0.0), ("m08", -0.8), ("m16", -1.6), ("m24", -2.4))
VG_CLOSED = (("08", 0.8), ("06", 0.6), ("04", 0.4), ("02", 0.2), ("00", 0.0))

C = ise.INSPECT
# размер, рамка (левый, правый, верхний, нижний), пределы осей — сняты с эталонов
FIG = {
    "z1_вах": dict(size=(736, 687), frame=(60, 728, 43, 613), xlim=(0, 4), ylim=(0, 0.3),
                   xstep=1, ystep=0.1, xlabel=("Vd", "V"), ylabel="Id (A)", fs=17, ytick_fs=8,
                   ylabel_fs=7, ylabel_x=22, xlabel_y=662, title_xy=(27, 6),
                   title="Gate:    Vg = 0.8,  0.0,  -0.8,  -1.6,  -2.4   (V)"),
    "z2_вах_по_h": dict(size=(769, 682), frame=(88, 760, 42, 609), xlim=(-2.775, 1.5), ylim=(0, 0.3),
                        xstep=1, ystep=0.1, xlabel=("Vg", "V"), ylabel="Id  (A)", fs=17,
                        ylabel_x=22, xlabel_y=655, title_xy=(38, 6),
                        title="Gate:   h = 0.05, 0.04, 0.03, 0.02, 0.01, 0.0 (mkm)"),
    "z3_порог": dict(size=(741, 656), frame=(101, 734, 43, 584), xlim=(-1.964, 1.5), ylim=(0, 0.15),
                     xstep=1, ystep=0.05, xlabel=("Vg", "V"), ylabel="Id  (A)", fs=17,
                     ylabel_x=26, xlabel_y=628, title_xy=(38, 6)),
    "z4_вах": dict(size=(751, 683), frame=(101, 738, 41, 612), xlim=(0, 4), ylim=(0, 0.15),
                   xstep=1, ystep=0.05, xlabel=("Vd", "V"), ylabel="Id  (A)", fs=17,
                   ylabel_x=26, xlabel_y=655, title_xy=(38, 4), lw=2,
                   title="Gate:   Vg = 0.8,   0.6,   0.4,   0.2,   0.0    (V)"),
}
NAMES = [("Задание 1. Выходные ВАХ, нормально открытый транзистор (h = %g мкм)" % H_OPEN, "z1_вах"),
         ("Задание 2. Передаточные ВАХ при Vd = 2 В, h = 0.05…0 мкм", "z2_вах_по_h"),
         ("Задание 3. Порог, нормально закрытый транзистор (h = %g мкм)" % H_CLOSED, "z3_порог"),
         ("Задание 4. Выходные ВАХ, нормально закрытый транзистор (h = %g мкм)" % H_CLOSED, "z4_вах")]


def iv(path, x, y="Drain TotalCurrent"):
    if not os.path.exists(path):
        return None
    d = viz.read_plt(path)
    return np.asarray(d[x]), np.asarray(d[y])


def threshold(V, I, vmax_frac=0.5):
    """Порог по методичке: x0 — локальный максимум второй производной в «пятке» ВАХ
    (первый заметный максимум слева, ниже резкого роста), через него — касательная к ВАХ,
    VT — её пересечение с осью Vg. Возвращает VT, x0, первую и вторую производные."""
    o = np.argsort(V); V, I = V[o], I[o]
    d1 = np.gradient(I, V); d2 = np.gradient(d1, V)
    top = d2.max()
    peaks = [i for i in range(1, len(V) - 1) if d2[i] >= d2[i - 1] and d2[i] > d2[i + 1] and d2[i] > 0.1 * top]
    i0 = peaks[0] if peaks else int(np.argmax(d2))
    x0 = V[i0]
    return x0 - I[i0] / d1[i0], x0, V, I, d1, d2


def figures():
    os.makedirs(OUT, exist_ok=True)
    made = []
    s = [iv(ISE + "task1/Vg_%s_t_msh.plt" % p, "Drain OuterVoltage") for p, _ in VG_OPEN]
    if all(c is not None for c in s):
        ise.xy_inspect([(c[0], c[1], C[k]) for k, c in enumerate(s)], OUT + "z1_вах.png", **FIG["z1_вах"])
        made.append("z1_вах")
    s = [iv(ISE + "task2_h%03d/New_t_msh.plt" % round(h * 1000), "Gate OuterVoltage") for h in H_SCAN]
    t3 = iv(ISE + "task3/New_t_msh.plt", "Gate OuterVoltage")
    k = H_SCAN.index(H_CLOSED)
    if s[k] is not None and t3 is not None and s[k][0].max() < 1.5 - 1e-3:
        # та же структура и тот же Vd: недостающий конец кривой — из задания 3
        m = t3[0] > s[k][0].max()
        s[k] = (np.concatenate([s[k][0], t3[0][m]]), np.concatenate([s[k][1], t3[1][m]]))
    lad = iv(ISE + "task2_h000_ladder/New_t_msh.plt", "Gate OuterVoltage")
    k0 = H_SCAN.index(0.0)
    if s[k0] is not None and lad is not None:
        # h = 0: обычная развёртка обрывается у 0.2 В, дальше — точки «лесенки» прыжков
        m = lad[0] > s[k0][0].max()
        s[k0] = (np.concatenate([s[k0][0], lad[0][m]]), np.concatenate([s[k0][1], lad[1][m]]))
    if any(c is not None for c in s):
        ise.xy_inspect([(c[0], c[1], C[k]) for k, c in enumerate(s) if c is not None],
                       OUT + "z2_вах_по_h.png", **FIG["z2_вах_по_h"])
        made.append("z2_вах_по_h")
    c = iv(ISE + "task3/New_t_msh.plt", "Gate OuterVoltage")
    if c is not None:
        vt, x0, V, I, d1, d2 = threshold(*c)
        # как на эталоне: x0 и VT близки, и порогом берётся x0 (замечание 1 методических указаний)
        f = dict(FIG["z3_порог"], title="Gate:   h = %g (mkm),   VT = %.2f (V)" % (H_CLOSED, x0))
        # как на эталоне: первая производная уменьшена вдвое, вторая — в пять раз
        ise.xy_inspect([(V, I, C[0]), (V, d1 / 2, C[1], ":"), (V, d2 / 5, C[3])], OUT + "z3_порог.png", **f)
        made.append("z3_порог")
        print("задание 3: максимум второй производной x0 = %.3f В (порог), касательная — %.3f В" % (x0, vt))
    s = [iv(ISE + "task4/Vg_%s_t_msh.plt" % p, "Drain OuterVoltage") for p, _ in VG_CLOSED]
    if all(c is not None for c in s):
        ise.xy_inspect([(c[0], c[1], C[k]) for k, c in enumerate(s)], OUT + "z4_вах.png", **FIG["z4_вах"])
        made.append("z4_вах")
    return made


def comparison_grid():
    """Эталон и ISE рядом, одной картинкой."""
    rows = [(lab.split(". ", 1)[1], [REF + f + ".png", OUT + f + ".png"]) for lab, f in NAMES]
    sheet.grid(rows, ["эталон", "ISE"], os.path.join(HERE, "results", "сравнение.png"))


if __name__ == "__main__":
    print("построено:", figures())
    comparison_grid()
