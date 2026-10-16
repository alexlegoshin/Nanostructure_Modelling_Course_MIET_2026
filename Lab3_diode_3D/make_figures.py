# -*- coding: utf-8 -*-
"""Все картинки лабы 3 из уже посчитанных данных — ISE не нужен.

    python3 Lab3_diode_3D/make_figures.py

Берёт выгруженные из ISE файлы (ise/) и результаты своего решателя (python/),
рисует восемь позиций задания в двух вариантах и собирает сводные листы
рядом с эталоном из методички (reference/).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

import numpy as np
import dfise, viz, sheet
import ise_style as ise
import ise3d, py3d_plots as pp

ISE = os.path.join(HERE, "ise") + "/"
PY = os.path.join(HERE, "python") + "/"
REF = os.path.join(HERE, "reference") + "/"
OUT_ISE = os.path.join(HERE, "results", "ise") + "/"
OUT_PY = os.path.join(HERE, "results", "python") + "/"

LX, LY, LZ = 1.0, 3.0, 0.8
ANODE = {"A": (0, 1, 1, 2), "B": (0.5, 1, 1, 2)}   # (x0, y0, x1, y1), мкм
ise3d.ZSTRETCH = 1.45

NAMES = [("Задание 1. Структура, диод A (полный анод)", "z1_структура_A"),
         ("Задание 1. Структура, диод B (половинный анод)", "z1_структура_B"),
         ("Задание 2. ВАХ обоих диодов", "z2_вах"),
         ("Задание 2. Плотность тока вдоль верхней границы сечения y=1.5", "z2_ток_вдоль_границы"),
         ("Задание 3. Диод A, сечение y=1.5", "z3_A_сечение_y1.5"),
         ("Задание 3. Диод B, сечение y=1.5", "z3_B_сечение_y1.5"),
         ("Задание 3. Диод B, сечение x=0.75", "z3_B_сечение_x0.75"),
         ("Задание 3. Диод B, сечение x=0.25", "z3_B_сечение_x0.25")]
TITLE = ("Лабораторная работа 3 — 3D диод с резким p-n переходом\n"
         "Вариант 2:  d = 0.8 мкм,  NB = 1.4e+17,  NAs = 1.0e+17")


def iv_ise(f):
    d = viz.read_plt(f)
    V = np.asarray(d["Anode OuterVoltage"]); I = np.asarray(d["Anode TotalCurrent"])
    o = np.argsort(V)
    return V[o], I[o]


def j_abs(d):
    v = np.asarray(d["TotalCurrentDensity-Vector"])
    return np.sqrt((v ** 2).sum(1)) if v.ndim == 2 else np.abs(v)


def figures_ise():
    """Восемь позиций по данным ISE. Диод B в ISE до 4 В не досчитался."""
    os.makedirs(OUT_ISE, exist_ok=True)
    for t in "AB":
        ise3d.structure(OUT_ISE + "z1_структура_%s.png" % t, ISE + "s%s_msh.grd" % t,
                        ISE + "s%s_msh.dat" % t, LX, LY, LZ, ANODE[t])
    VA, IA = iv_ise(ISE + "sA_des.plt"); VB, IB = iv_ise(ISE + "sB_des.plt")
    # чёрная — диод B, красная — A, как в эталоне
    ise.xy([("I (A)", VB, IB, "k"), ("I (A)", VA, IA, "r")],
           OUT_ISE + "z2_вах.png", size=(497, 462), legend=False)
    a = viz.read_plt(ISE + "AyTop.plt"); b = viz.read_plt(ISE + "ByTop.plt")
    ise.xy([("J (A/cm^2)", np.asarray(b["Distance"]), j_abs(b), "k"),
            ("J (A/cm^2)", np.asarray(a["Distance"]), j_abs(a), "r")],
           OUT_ISE + "z2_ток_вдоль_границы.png", size=(484, 510), legend=False)
    for nm, base, kind, t in (("z3_A_сечение_y1.5", "Ay", "y", "A"),
                              ("z3_B_сечение_y1.5", "By", "y", "B"),
                              ("z3_B_сечение_x0.75", "Bx75", "x0.75", "B"),
                              ("z3_B_сечение_x0.25", "Bx25", "x0.25", "B")):
        g = dfise.read_grid(ISE + base + ".grd"); d = dfise.read_dataset(ISE + base + ".dat", g)
        ise3d.cut_in_box(OUT_ISE + nm + ".png", LX, LY, LZ, ANODE[t], g, d["SpaceCharge"], kind)
    print("ISE: A до %.2f В (%.5f А), B до %.2f В" % (VA.max(), IA[-1], VB.max()))
    return VB.max()


def figures_python():
    """Те же восемь позиций по своему решателю (python/sweep.py)."""
    os.makedirs(OUT_PY, exist_ok=True)
    # структура одна и та же — это геометрия и легирование, а не решение
    for t in "AB":
        ise3d.structure(OUT_PY + "z1_структура_%s.png" % t, ISE + "s%s_msh.grd" % t,
                        ISE + "s%s_msh.dat" % t, LX, LY, LZ, ANODE[t])
    A = np.load(PY + "iv_A.npz"); B = np.load(PY + "iv_B.npz")
    ise.xy([("I (A)", B["V"], B["I"], "k"), ("I (A)", A["V"], A["I"], "r")],
           OUT_PY + "z2_вах.png", size=(497, 462), legend=False)
    xa, ja = pp.j_top(PY + "field_A.npz", ANODE["A"])
    xb, jb = pp.j_top(PY + "field_B.npz", ANODE["B"])
    ise.xy([("J (A/cm^2)", xb, jb, "k"), ("J (A/cm^2)", xa, ja, "r")],
           OUT_PY + "z2_ток_вдоль_границы.png", size=(484, 510), legend=False)
    zA = np.load(PY + "field_A.npz"); zB = np.load(PY + "field_B.npz")
    pp.cut_in_box(OUT_PY + "z3_A_сечение_y1.5.png", zA, "y", 1.5, anode=ANODE["A"])
    pp.cut_in_box(OUT_PY + "z3_B_сечение_y1.5.png", zB, "y", 1.5, anode=ANODE["B"])
    pp.cut_in_box(OUT_PY + "z3_B_сечение_x0.75.png", zB, "x", 0.75, anode=ANODE["B"])
    pp.cut_in_box(OUT_PY + "z3_B_сечение_x0.25.png", zB, "x", 0.25, anode=ANODE["B"])
    print("питон: A %.5f А, B %.5f А при 4 В" % (A["I"][-1], B["I"][-1]))


if __name__ == "__main__":
    vb = figures_ise()
    figures_python()
    # диод B в ISE под смещением не сошёлся — помечаем позиции, где он нужен
    nb = "ISE: диод B под смещением не сошёлся (есть только %.0f В)" % vb
    notes = {"z2_вах": "ISE: кривая B не посчитана, только A",
             "z2_ток_вдоль_границы": "ISE: кривая B — при 0 В, не при 4 В",
             "z3_B_сечение_y1.5": nb, "z3_B_сечение_x0.75": nb, "z3_B_сечение_x0.25": nb}
    sheet.pairs([(t, REF + f + ".png", OUT_ISE + f + ".png", notes.get(f, ""))
                 for t, f in NAMES], OUT_ISE + "СВОДНЫЙ_ЛИСТ.png", title=TITLE)
    sheet.pairs([(t, REF + f + ".png", OUT_PY + f + ".png", "") for t, f in NAMES],
                OUT_PY + "СВОДНЫЙ_ЛИСТ.png", title=TITLE)
    print("сводные листы собраны")
