# -*- coding: utf-8 -*-
"""Лаба 3 в DEVSIM на неструктурированной сетке Gmsh — одной командой.

    python run.py A              # диод A, мелкая сетка (~104 тыс. узлов)
    python run.py B              # диод B
    python run.py A --scale 1.5  # сетка в 1.5 раза крупнее (~34 тыс. узлов)

Что делает: строит сетку (tools/mesh3d.py, кэшируется в mesh_<диод>_<scale>.msh),
решает равновесие, включает дрейф-диффузию и разворачивает анод до --vmax.
Пишет iv_<диод>_<scale>_<подвижность>.json (V, I) и поля при Vmax в field_*.npz
(узлы, тетраэдры, потенциал, n, p, легирование, ток узлов) — по ним рисует make_figures.py.

Площади ячеек здесь — как считает сам DEVSIM, то есть завышенные (до двух раз на
сетке Gmsh, см. tools/voronoi3d.py); поэтому и токи завышены. Расчёт с поправкой
и физикой ISE — run_ise.py.

Память — главное ограничение. Прямой решатель (UMFPACK) обязателен: итерационный
GMRES под смещением выдаёт «сходимость» на неправильном решении. Замеры на M1:
34 тыс. узлов — около 2.6 ГБ, 104 тыс. — оценка около 10 ГБ. На 8 ГБ мелкая
сетка не помещается, считать на машине с 16–32 ГБ. Видеокарта — по желанию, --direct cudss.
"""
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))

import mesh3d

ANODE = {"A": (0.0, 1.0, 1.0, 2.0), "B": (0.5, 1.0, 1.0, 2.0)}


def peak_mb():
    """Пиковая память процесса, МБ: на Windows — PeakWorkingSetSize, иначе ru_maxrss."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (n, ctypes.c_size_t) for n in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        c = PMC(); c.cb = ctypes.sizeof(c)
        k32 = ctypes.WinDLL("kernel32")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        gpmi = ctypes.WinDLL("psapi").GetProcessMemoryInfo
        gpmi.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        gpmi(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return c.PeakWorkingSetSize / 2 ** 20
    import resource
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 1024 / 1024 if sys.platform == "darwin" else r / 1024


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("diode", choices=["A", "B"])
    ap.add_argument("--scale", type=float, default=1.0, help="множитель шагов сетки, больше = грубее")
    ap.add_argument("--vmax", type=float, default=4.0)
    ap.add_argument("--step", type=float, default=0.1)
    ap.add_argument("--solver", default="direct", choices=["direct", "iterative"])
    ap.add_argument("--direct", default="umfpack", choices=["umfpack", "pardiso", "cudss"],
                    help="прямой решатель; Pardiso из MKL 2025 на FX-8320 врёт (см. dev3d.use_direct)")
    ap.add_argument("--relerr", type=float, default=1e-8, help="допуск Ньютона под смещением")
    ap.add_argument("--mobility", default="edge", choices=["edge", "element", "constant"],
                    help="edge — Коги-Томас + насыщение по полю вдоль ребра (как dd3d), "
                         "element — насыщение по полному |E| на тетраэдре, "
                         "constant — постоянная 400/200 из simple_physics")
    a = ap.parse_args()

    tag = "%s_%g" % (a.diode, a.scale)
    msh = os.path.join(HERE, "mesh_%s.msh" % tag)
    if not os.path.exists(msh):
        k = a.scale
        info = mesh3d.build(msh, ANODE[a.diode], h_far=0.10 * k, h_junc=0.012 * k,
                            h_anode=0.015 * k, h_edge=0.006 * k)
        print("сетка: %d узлов, %d тетраэдров" % (info["nodes"], info["tets"]), flush=True)

    import devsim as ds
    import dev3d
    dev3d.SOLVER, dev3d.RELERR = a.solver, a.relerr
    dev3d.MOBILITY = {"edge": "ct", "element": "element", "constant": "const"}[a.mobility]
    print("прямой решатель: %s" % dev3d.use_direct(a.direct), flush=True)
    t0 = time.time()
    dev3d.load(msh)
    dev3d.equilibrium()
    print("равновесие: %.0f с, память %.0f МБ" % (time.time() - t0, peak_mb()), flush=True)
    tol0 = dev3d.drift_diffusion()
    print("дрейф-диффузия при 0 В (допуск %g): %.0f с, память %.0f МБ"
          % (tol0, time.time() - t0, peak_mb()), flush=True)

    rtag = "%s_%s" % (tag, a.mobility)
    out = os.path.join(HERE, "iv_%s.json" % rtag)
    iv = dev3d.ramp(a.vmax, a.step, log=lambda s: print(s, flush=True))
    json.dump(iv, open(out, "w"))
    dev3d.save_fields(os.path.join(HERE, "field_%s.npz" % rtag))
    print("готово за %.0f с, пиковая память %.0f МБ, ВАХ в %s"
          % (time.time() - t0, peak_mb(), out), flush=True)


if __name__ == "__main__":
    main()
