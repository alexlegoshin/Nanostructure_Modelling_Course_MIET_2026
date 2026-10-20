# -*- coding: utf-8 -*-
"""Диод лабы 3 в DEVSIM с физикой ISE — на сетке и легировании самого ISE.

    python run_ise.py A                   # сетка ise/sA_msh.grd + sA_msh.dat, до 4 В
    python run_ise.py A --vmax 1 --ni 1.1e10
    python run_ise.py B                   # B на сетке A: анод — её правая половина (x >= 0.5)

Пишет iv_ise_<диод>.json и печатает сравнение с ВАХ ISE (ise/s<диод>_des.plt), если она есть.
Физика и её соответствие командному файлу ISE — в tools/dev_ise.py.
"""
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
ISE = os.path.join(HERE, "..", "ise")

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("diode", choices=["A", "B"])
    ap.add_argument("--vmax", type=float, default=4.0)
    ap.add_argument("--step", type=float, default=0.1, help="начальный шаг, В")
    ap.add_argument("--maxstep", type=float, default=0.2, help="как MaxStep=0.05 у ISE: 0.05·4 В")
    ap.add_argument("--ext-below", type=float, default=None, help="float128 только ниже этого V")
    ap.add_argument("--ni", type=float, default=None, help="собственная концентрация, см^-3")
    ap.add_argument("--no-hfs", action="store_true", help="без насыщения скорости")
    ap.add_argument("--direct", default="umfpack", choices=["umfpack", "pardiso", "cudss"])
    ap.add_argument("--mesh", default="A", choices=["A", "own"],
                    help="для B: A — сетка диода A с анодом x>=0.5 (как у преподавателя: командные "
                         "файлы сетки A и B одинаковы), own — ise/sB_msh.grd (огрублённая при наших попытках)")
    ap.add_argument("--tag", default="", help="добавка к имени файла результата")
    a = ap.parse_args()

    import devsim as ds
    import dev3d, dev_ise, ise_grid, viz
    from run import peak_mb
    print("прямой решатель:", dev3d.use_direct(a.direct), flush=True)
    if a.ni:
        dev_ise.NI = a.ni
    if a.ext_below is not None:
        dev_ise.EXT_BELOW = a.ext_below

    src = "A" if a.diode == "B" and a.mesh == "A" else a.diode
    g = ise_grid.load(os.path.join(ISE, "s%s_msh.grd" % src), os.path.join(ISE, "s%s_msh.dat" % src))
    if src != a.diode:
        # анод B — правая половина анода A: линия x = 0.5 на сетке A — линия узлов,
        # ни один треугольник анода её не пересекает (проверено), так что вырезается точно
        mat, tri = g["contacts"]["Anode"]
        keep = g["vertices"][tri][:, :, 0].min(axis=1) >= 0.5 - 1e-9
        g["contacts"]["Anode"] = (mat, tri[keep])
        print("анод B вырезан из сетки A: %d треугольников из %d" % (keep.sum(), len(tri)), flush=True)
    print("сетка ISE (%s): %d узлов" % (src, len(g["vertices"])), flush=True)
    t0 = time.time()
    dev_ise.create_device(dev_ise.mesh_from_ise(g), g["donors"], g["acceptors"])
    dev_ise.setup(field_dependent=not a.no_hfs)
    print("равновесие: %.0f с, память %.0f МБ, n_i=%g" % (time.time() - t0, peak_mb(), dev_ise.NI), flush=True)
    iv = dev_ise.ramp(a.vmax, a.step, a.maxstep, log=lambda s: print(s, flush=True))
    out = os.path.join(HERE, "iv_ise_%s%s.json" % (a.diode, a.tag))
    json.dump(iv, open(out, "w"))
    print("готово за %.0f с, пиковая память %.0f МБ, ВАХ в %s" % (time.time() - t0, peak_mb(), out), flush=True)

    plt = os.path.join(ISE, "s%s_des.plt" % a.diode)
    if os.path.exists(plt):
        d = viz.read_plt(plt)
        Vi, Ii = np.asarray(d["Anode OuterVoltage"]), np.abs(np.asarray(d["Anode TotalCurrent"]))
        V, I = np.array(iv).T
        print("\n   V      ISE, А       DEVSIM, А    DEVSIM/ISE")
        for v in (0.3, 0.5, 0.7, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0):
            if v <= min(Vi.max(), V.max()) + 1e-9:
                i1 = np.exp(np.interp(v, Vi, np.log(np.maximum(Ii, 1e-30))))
                i2 = np.exp(np.interp(v, V, np.log(np.maximum(np.abs(I), 1e-30))))
                print("  %.2f  %11.4e  %11.4e  %8.4f" % (v, i1, i2, i2 / i1))


if __name__ == "__main__":
    main()
