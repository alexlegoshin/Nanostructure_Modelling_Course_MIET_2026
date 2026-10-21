# -*- coding: utf-8 -*-
"""Все иллюстрации работы 3 из уже посчитанных данных — ISE не нужен.

    python3 Lab3_diode_3D/make_figures.py            # ISE, самописный решатель, DEVSIM
    python3 Lab3_diode_3D/make_figures.py 1 edge     # плюс DEVSIM на сетке Gmsh (run.py, scale 1)

Каждая позиция рисуется в размере и ракурсе своей эталонной иллюстрации
(reference/): камера для трёхмерных картинок подгоняется по самому эталону
(ise3d.fit_camera), графики — в его рамке и с его засечками (ise_style.xy_ref).
Так картинки всех столбцов совпадают с эталоном по размеру попиксельно.
"""
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

import numpy as np
import dfise, viz, sheet
import ise_style as ise
import ise3d, py3d_plots as pp

ISE = os.path.join(HERE, "ise") + "/"
PY = os.path.join(HERE, "python") + "/"
REF = os.path.join(HERE, "reference") + "/"
DS = os.path.join(HERE, "devsim") + "/"
OUT = {k: os.path.join(HERE, "results", k) + "/" for k in ("ise", "python", "devsim_ise")}

LX, LY, LZ = 1.0, 3.0, 0.8
ANODE = {"A": (0, 1, 1, 2), "B": (0.5, 1, 1, 2)}   # (x0, y0, x1, y1), мкм

NAMES = [("Задание 1. Структура, диод A (полный анод)", "z1_структура_A"),
         ("Задание 1. Структура, диод B (половинный анод)", "z1_структура_B"),
         ("Задание 2. ВАХ обоих диодов", "z2_вах"),
         ("Задание 2. Плотность тока вдоль верхней границы сечения y=1.5", "z2_ток_вдоль_границы"),
         ("Задание 3. Диод A, сечение y=1.5", "z3_A_сечение_y1.5"),
         ("Задание 3. Диод B, сечение y=1.5", "z3_B_сечение_y1.5"),
         ("Задание 3. Диод B, сечение x=0.75", "z3_B_сечение_x0.75"),
         ("Задание 3. Диод B, сечение x=0.25", "z3_B_сечение_x0.25")]
CUTS = [("z3_A_сечение_y1.5", "A", "y", 1.5), ("z3_B_сечение_y1.5", "B", "y", 1.5),
        ("z3_B_сечение_x0.75", "B", "x", 0.75), ("z3_B_сечение_x0.25", "B", "x", 0.25)]
TITLE = ("Лабораторная работа 3 — 3D диод с резким p-n переходом\n"
         "Вариант 2:  d = 0.8 мкм,  NB = 1.4e+17,  NAs = 1.0e+17")

# рамки графиков эталона, px: (левый, правый, верхний, нижний) — сняты с reference/*.png
IV = dict(size=(477, 482), frame=(103, 470, 6, 417), xlabel=("U", "V"), ylabel="I  (A)",
          xstep=1, ystep=0.002, yfmt="{:.3f}", xlabel_y=468)
JT = dict(size=(498, 503), frame=(113, 491, 4, 438), xlabel=("x", "mkm"), ylabel="J  (A/cm^2)",
          xstep=0.2, ystep=100000, xfmt="{:g}", yfmt="{:.0f}", xlabel_y=486)


def jt(series, path, **kw):
    """График тока вдоль границы: шаг засечек по Y — по диапазону данных, как у inspect."""
    ys = np.concatenate([np.asarray(s[1], float) for s in series])
    span = (kw.get("ylim") or (ys.min(), ys.max()))
    span = span[1] - span[0]
    step = 100000 if span <= 6e5 else 200000 if span <= 1.6e6 else 500000
    ise.xy_ref(series, path, **{**JT, "ystep": step, **kw})

_CAM = {}


def camera(name, diode):
    """Камера эталонной картинки (подгоняется один раз на позицию)."""
    if name not in _CAM:
        kind = "structure" if name.startswith("z1") else "cut"
        cam, size, err = ise3d.fit_camera(REF + name + ".png", kind, ANODE[diode], LX, LY, LZ)
        _CAM[name] = (cam, size)
    return _CAM[name]


def iv_ise(f):
    d = viz.read_plt(f)
    V = np.asarray(d["Anode OuterVoltage"]); I = np.asarray(d["Anode TotalCurrent"])
    o = np.argsort(V)
    return V[o], I[o]


def j_abs(d):
    v = np.asarray(d["TotalCurrentDensity-Vector"])
    return np.sqrt((v ** 2).sum(1)) if v.ndim == 2 else np.abs(v)


def plane(kind, value, u, w, F):
    """Срез (u — x или y, w — z, в мкм; F[u, w]) -> точки плоскости и цвета полос."""
    U, W = np.meshgrid(u, w, indexing="ij")
    P3 = (np.stack([U, np.full_like(U, value), W], -1) if kind == "y"
          else np.stack([np.full_like(U, value), U, W], -1))
    return P3, ise3d.bands_rgba(F)


def structure(out, name, diode, verts, tris, dop):
    cam, size = camera(name, diode)
    ise3d.structure_ref(out + name + ".png", verts, tris, dop, LX, LY, LZ, ANODE[diode], cam, size)


def cut(out, name, diode, kind, value, P3, rgba):
    cam, size = camera(name, diode)
    ise3d.cut_ref(out + name + ".png", P3, rgba, kind, value, LX, LY, LZ, ANODE[diode], cam, size)


def figures_ise():
    """ISE: диод A полностью; диод B под смещением не сошёлся, поэтому для него только структура."""
    out = OUT["ise"]; os.makedirs(out, exist_ok=True)
    for t in "AB":
        g = dfise.read_grid3d(ISE + "s%s_msh.grd" % t)
        dop = dfise.read_dataset(ISE + "s%s_msh.dat" % t)["DopingConcentration"]
        structure(out, "z1_структура_" + t, t, g["vertices"], g["surface"], dop)
    VA, IA = iv_ise(ISE + "sA_des.plt")
    ise.xy_ref([(VA, IA, "r")], out + "z2_вах.png", **IV)
    a = viz.read_plt(ISE + "AyTop.plt"); ja = j_abs(a)
    jt([(np.asarray(a["Distance"]), ja, "r")], out + "z2_ток_вдоль_границы.png", ylim=(0, ja.max()))
    g = dfise.read_grid(ISE + "Ay.grd"); d = dfise.read_dataset(ISE + "Ay.dat", g)
    cut(out, "z3_A_сечение_y1.5", "A", "y", 1.5, *ise3d.plane_from_ise_cut(g, d["SpaceCharge"], "y", 1.5))
    for f in ("z3_B_сечение_y1.5", "z3_B_сечение_x0.75", "z3_B_сечение_x0.25"):
        if os.path.exists(out + f + ".png"):     # сечения диода B при 0 В — не результат
            os.remove(out + f + ".png")
    print("ISE: A до %.2f В (%.5f А)" % (VA.max(), IA[-1]))


def figures_python():
    """Самописный решатель: тензорная сетка, структуры не рисуются."""
    out = OUT["python"]; os.makedirs(out, exist_ok=True)
    for t in "AB":
        if os.path.exists(out + "z1_структура_%s.png" % t):
            os.remove(out + "z1_структура_%s.png" % t)
    A = np.load(PY + "iv_A.npz"); B = np.load(PY + "iv_B.npz")
    ise.xy_ref([(B["V"], B["I"], "k"), (A["V"], A["I"], "r")], out + "z2_вах.png", **IV)
    xa, ja = pp.j_top_abs(PY + "field_A.npz")         # |J| на верхней линии, как у эталона
    xb, jb = pp.j_top_abs(PY + "field_B.npz")
    jt([(xb, jb, "k"), (xa, ja, "r")], out + "z2_ток_вдоль_границы.png")
    z = {"A": np.load(PY + "field_A.npz"), "B": np.load(PY + "field_B.npz")}
    for nm, t, kind, value in CUTS:
        cut(out, nm, t, kind, value, *plane(kind, value, *pp.cut_plane(z[t], kind, value)))
    print("самописный решатель: A %.5f А, B %.5f А при 4 В" % (A["I"][-1], B["I"][-1]))


def figures_devsim(name, fA, fB, ivA, ivB):
    """DEVSIM (devsim/run_ise.py — основной, или run.py на сетке Gmsh)."""
    files = [DS + f for f in (fA, fB, ivA, ivB)]
    if not all(os.path.exists(f) for f in files):
        print("DEVSIM %s: нет файлов, пропускаю" % name)
        return None
    out = os.path.join(HERE, "results", name) + "/"; os.makedirs(out, exist_ok=True)
    z = {"A": np.load(files[0]), "B": np.load(files[1])}
    iv = {"A": np.array(json.load(open(files[2]))), "B": np.array(json.load(open(files[3])))}
    for t in "AB":
        v = np.stack([z[t]["x"], z[t]["y"], z[t]["z"]], 1) * 1e4
        structure(out, "z1_структура_" + t, t, v, pp.devsim_surface(z[t]), z[t]["C"])
    ise.xy_ref([(iv["B"][:, 0], iv["B"][:, 1], "k"), (iv["A"][:, 0], iv["A"][:, 1], "r")],
               out + "z2_вах.png", **IV)
    if "edge_j" in z["A"].files:                       # |J| на верхней линии, как у эталона
        xa, ja, _ = pp.devsim_j_top_abs(files[0]); xb, jb, _ = pp.devsim_j_top_abs(files[1])
    else:                                              # сетка Gmsh: только ток в контакт
        xa, ja, _ = pp.devsim_j_top(files[0], ANODE["A"]); xb, jb, _ = pp.devsim_j_top(files[1], ANODE["B"])
    jt([(xb, jb, "k"), (xa, ja, "r")], out + "z2_ток_вдоль_границы.png")
    for nm, t, kind, value in CUTS:
        cut(out, nm, t, kind, value, *plane(kind, value, *pp.devsim_cut(z[t], kind, value)))
    return out


def comparison_grid():
    """Вся таблица работы 3 одной картинкой: эталон, ISE, самописный решатель, DEVSIM."""
    labels = ["Структура, диод A", "Структура, диод B", "ВАХ обоих диодов",
              "Плотность тока вдоль верхней границы сечения y = 1.5", "Диод A, сечение y = 1.5",
              "Диод B, сечение y = 1.5", "Диод B, сечение x = 0.75", "Диод B, сечение x = 0.25"]
    rows = [(lab, [REF + f + ".png"] + [OUT[k] + f + ".png" for k in ("ise", "python", "devsim_ise")])
            for lab, (_, f) in zip(labels, NAMES)]
    sheet.grid(rows, ["эталон", "ISE", "самописный решатель", "DEVSIM"],
               os.path.join(HERE, "results", "сравнение.png"))


def sheets():
    for k, sub in (("ise", "ISE (диод B под смещением не сошёлся)"), ("python", "самописный решатель"),
                   ("devsim_ise", "DEVSIM, физика и сетка ISE")):
        out = OUT[k]
        items = [(t, REF + f + ".png", out + f + ".png") for t, f in NAMES if os.path.exists(out + f + ".png")]
        sheet.pairs(items, out + "СВОДНЫЙ_ЛИСТ.png", title=TITLE + "\n" + sub)


if __name__ == "__main__":
    figures_ise()
    figures_python()
    figures_devsim("devsim_ise", "field_ise_A_isemesh_clip.npz", "field_ise_B_isemeshA_clip.npz",
                   "iv_ise_A_isemesh_clip.json", "iv_ise_B_isemeshA_clip.json")
    if len(sys.argv) > 1:                         # сетка Gmsh (run.py): <scale> [<подвижность>]
        sc, mob = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "edge")
        figures_devsim("devsim_gmsh_%s" % sc, "field_A_%s_%s.npz" % (sc, mob), "field_B_%s_%s.npz" % (sc, mob),
                       "iv_A_%s_%s.json" % (sc, mob), "iv_B_%s_%s.json" % (sc, mob))
    sheets()
    comparison_grid()
    print("сводные листы и сетка сравнения собраны")
