# -*- coding: utf-8 -*-
"""Лаба 3 в DEVSIM на неструктурированной сетке Gmsh — одной командой.

    python run.py A              # диод A, мелкая сетка (~104 тыс. узлов)
    python run.py B              # диод B
    python run.py A --scale 1.5  # сетка в 1.5 раза крупнее (~34 тыс. узлов)
    python run.py A --scale 2 --relerr 1e-5   # ~15 тыс. узлов, ~2 ГБ — проверка на ноутбуке

Что делает: строит сетку (tools/mesh3d.py, кэшируется в mesh_<диод>_<scale>.msh),
решает равновесие, включает дрейф-диффузию и разворачивает анод до --vmax.
Пишет iv_<диод>_<scale>_<подвижность>.json (V, I) и поле diode_*.tec (Tecplot ASCII).
Подвижность по умолчанию — element: Коги-Томас + насыщение скорости по полному |E|
на тетраэдре (см. tools/dev3d.py, почему не по ребру).

Память — главное ограничение. Прямой решатель (UMFPACK) обязателен: итерационный
GMRES под смещением выдаёт «сходимость» на неправильном решении. Замеры на M1:
34 тыс. узлов — около 2.6 ГБ, 104 тыс. — оценка около 10 ГБ. На 8 ГБ мелкая
сетка не помещается, считать на машине с 16–32 ГБ. Видеокарта не используется.
"""
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))

import mesh3d

ANODE = {"A": (0.0, 1.0, 1.0, 2.0), "B": (0.5, 1.0, 1.0, 2.0)}


def peak_mb():
    """Пиковая память процесса, МБ. На Windows модуля resource нет — через WinAPI."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        k32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        c = PMC(); c.cb = ctypes.sizeof(PMC)
        psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return c.PeakWorkingSetSize / 1024 / 1024
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
    ap.add_argument("--mobility", default="element", choices=["element", "field", "constant"],
                    help="Коги-Томас + насыщение скорости: element — по |E| на тетраэдре, "
                         "field — по проекции на ребро; constant — 400/200")
    ap.add_argument("--relerr", type=float, default=1e-8, help="допуск Ньютона; на грубых сетках 1e-5")
    a = ap.parse_args()

    tag = "%s_%g" % (a.diode, a.scale)
    mtag = "%s_%s" % (tag, a.mobility)
    msh = os.path.join(HERE, "mesh_%s.msh" % tag)
    if not os.path.exists(msh):
        k = a.scale
        info = mesh3d.build(msh, ANODE[a.diode], h_far=0.10 * k, h_junc=0.012 * k,
                            h_anode=0.015 * k, h_edge=0.006 * k)
        print("сетка: %d узлов, %d тетраэдров" % (info["nodes"], info["tets"]), flush=True)

    import devsim as ds
    import dev3d
    dev3d.SOLVER, dev3d.RELERR, dev3d.MOBILITY = a.solver, a.relerr, a.mobility
    t0 = time.time()
    dev3d.load(msh)
    dev3d.equilibrium()
    print("равновесие: %.0f с, память %.0f МБ" % (time.time() - t0, peak_mb()), flush=True)
    dev3d.drift_diffusion()
    print("дрейф-диффузия при 0 В: %.0f с, память %.0f МБ" % (time.time() - t0, peak_mb()), flush=True)

    out = os.path.join(HERE, "iv_%s.json" % mtag)
    iv = dev3d.ramp(a.vmax, a.step, log=lambda s: print(s, flush=True))
    json.dump(iv, open(out, "w"))
    ds.write_devices(file=os.path.join(HERE, "diode_%s.tec" % mtag), type="tecplot")
    print("готово за %.0f с, пиковая память %.0f МБ, ВАХ в %s"
          % (time.time() - t0, peak_mb(), out), flush=True)


if __name__ == "__main__":
    main()
