# -*- coding: utf-8 -*-
"""Самописный решатель с физикой ISE (tools/dd3d_ise.py): развёртка диода до 4 В.

    python sweep_ise.py A 1            # тензорная сетка на осях сетки ISE, деление 1 (как DEVSIM --tensor 1)
    python sweep_ise.py B 3 --gpu      # деление 3 (~250 тыс. узлов), линейные системы на видеокарте

Пишет iv_ise_<диод>_t<деление>.npz (V, I) и field_ise_<диод>_t<деление>.npz (поля при последнем V).
"""
import argparse, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
ISE = os.path.join(HERE, "..", "ise")
ANODE = {"A": (0.0, 1.0, 1.0, 2.0), "B": (0.5, 1.0, 1.0, 2.0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("diode", choices=["A", "B"])
    ap.add_argument("split", type=int, help="деление каждого отрезка осей сетки ISE")
    ap.add_argument("--gpu", action="store_true")
    ap.add_argument("--vmax", type=float, default=4.0)
    ap.add_argument("--isedir", default=ISE, help="каталог с sA_msh.grd, с осей которой строится сетка")
    ap.add_argument("--tol", type=float, default=1e-6, help="невязка Гуммеля по квазиуровням, В")
    ap.add_argument("--coarse", action="store_true", help="редкий набор напряжений (14 точек)")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    import dfise, tensor_mesh, dd3d_ise
    v = dfise.read_grid3d(os.path.join(a.isedir, "sA_msh.grd"))["vertices"]
    xs, ys, zs = (tensor_mesh.refine(v[:, k], a.split) for k in range(3))
    t0 = time.time()
    d = dd3d_ise.Diode(xs, ys, zs, ANODE[a.diode], gpu=a.gpu)
    print("диод %s: сетка %d×%d×%d = %d узлов, %s, подготовка %.0f с"
          % (a.diode, d.nx, d.ny, d.nz, d.N, "GPU" if a.gpu else "CPU", time.time() - t0), flush=True)
    if a.coarse:   # мелкая сетка: 14 точек, на изломе гуще (каждая точка на насыщении — десятки итераций)
        volts = np.array([0.2, 0.4, 0.6, 0.8, 0.9, 1.0, 1.2, 1.4, 1.7, 2.0, 2.5, 3.0, 3.5, 4.0])
    else:
        volts = np.concatenate([np.arange(0.1, 0.8, 0.1), np.arange(0.8, 1.6, 0.05), np.arange(1.6, a.vmax + 1e-9, 0.1)])
    volts = volts[volts <= a.vmax + 1e-9]
    state, iv = d.sweep(volts, log=lambda s: print(s, flush=True), tol=a.tol)
    tag = "%s_t%d%s" % (a.diode, a.split, a.tag)
    V, I = np.array(iv).T
    np.savez(os.path.join(HERE, "iv_ise_%s.npz" % tag), V=V, I=I)
    np.savez_compressed(os.path.join(HERE, "field_ise_%s.npz" % tag), **d.fields(state))
    print("готово за %.0f с" % (time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
