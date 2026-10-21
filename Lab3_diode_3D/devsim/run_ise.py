# -*- coding: utf-8 -*-
"""Диод лабы 3 в DEVSIM с физикой ISE — на сетке и легировании самого ISE.

    python run_ise.py A                   # сетка ise/sA_msh.grd + sA_msh.dat, до 4 В
    python run_ise.py A --vmax 1 --ni 1.1e10
    python run_ise.py B                   # B на сетке A: анод — её правая половина (x >= 0.5)

Пишет iv_ise_<диод>_<сетка>.json, поля при Vmax — field_ise_<…>.npz (для make_figures.py)
и печатает сравнение с ВАХ ISE (ise/s<диод>_des.plt), если она есть.
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
    ap.add_argument("--drive", default=None, choices=["qf", "e", "elem"],
                    help="движущая сила насыщения: elem — |E| на тетраэдре (как у ISE), "
                         "e — поле вдоль ребра, qf — градиент квазиуровня Ферми")
    ap.add_argument("--direct", default="umfpack", choices=["umfpack", "pardiso", "cudss"])
    ap.add_argument("--mesh", default="A", choices=["A", "own"],
                    help="для B: A — сетка диода A с анодом x>=0.5 (как у преподавателя: командные "
                         "файлы сетки A и B одинаковы), own — ise/sB_msh.grd (огрублённая при наших попытках)")
    ap.add_argument("--box", default="clip", choices=["devsim", "signed", "clip"],
                    help="площади граней ячеек: devsim — как есть (завышены), signed — Вороной со знаком, "
                         "clip — со знаком, отрицательные в ноль (tools/voronoi3d.py)")
    ap.add_argument("--fast", action="store_true",
                    help="без float128 (мелкие сетки): ниже 0.7 В допуск 1e-5 — ток там ~1e-6 А и меньше")
    ap.add_argument("--lz", type=float, default=0.8,
                    help="толщина, мкм (по умолчанию 0.8 — вариант 2; сетка ISE масштабируется по z)")
    ap.add_argument("--tensor", type=int, default=0, metavar="N",
                    help="тензорная сетка на осях ISE, каждый отрезок делится на N (tools/tensor_mesh.py)")
    ap.add_argument("--gmsh", type=float, default=None, metavar="SCALE",
                    help="своя сетка Gmsh (tools/mesh3d.py) вместо сетки ISE; 1.0 — ~104 тыс. узлов")
    ap.add_argument("--tag", default="", help="добавка к имени файла результата")
    ap.add_argument("--isedir", default=None,
                    help="другой каталог с s<диод>_msh.grd/.dat и s<диод>_des.plt (например, прежняя "
                         "сетка ISE на 5751 узел из истории git: git show a30e494:Lab3_diode_3D/ise/...)")
    a = ap.parse_args()
    global ISE
    if a.isedir:
        ISE = a.isedir

    import devsim as ds
    import dev3d, dev_ise, ise_grid, viz
    from run import peak_mb
    print("прямой решатель:", dev3d.use_direct(a.direct), flush=True)
    if a.ni:
        dev_ise.NI = a.ni
    if a.drive:
        dev_ise.HFS_DRIVE = a.drive
    dev_ise.FAST = a.fast
    if a.ext_below is not None:
        dev_ise.EXT_BELOW = a.ext_below

    t0 = time.time()
    if a.gmsh:
        import mesh3d
        from run import ANODE
        msh = os.path.join(HERE, "mesh_%s_%g.msh" % (a.diode, a.gmsh))
        if not os.path.exists(msh):
            k = a.gmsh
            info = mesh3d.build(msh, ANODE[a.diode], h_far=0.10 * k, h_junc=0.012 * k,
                                h_anode=0.015 * k, h_edge=0.006 * k)
            print("сетка Gmsh: %d узлов, %d тетраэдров" % (info["nodes"], info["tets"]), flush=True)
        ds.create_gmsh_mesh(mesh="m", file=msh)
        dev_ise.create_device("m", junction=(1.4e17, 1.0e17, 0.4e-4))
        print("сетка Gmsh %s (scale %g)" % (os.path.basename(msh), a.gmsh), flush=True)
        if a.box != "devsim":
            import voronoi3d
            verts, tets = voronoi3d.read_msh(msh)
    elif a.tensor:
        import tensor_mesh
        from run import ANODE
        base = ise_grid.load(os.path.join(ISE, "sA_msh.grd"), os.path.join(ISE, "sA_msh.dat"))
        g = tensor_mesh.from_ise(base, a.tensor, ANODE[a.diode], lz=a.lz)
        print("тензорная сетка T%d (оси ISE, деление на %d): %d узлов, %d тетраэдров"
              % (a.tensor, a.tensor, len(g["vertices"]), len(g["bulk"]["SiW"][1])), flush=True)
        dev_ise.create_device(dev_ise.mesh_from_ise(g), g["donors"], g["acceptors"])
        verts, tets = g["vertices"], g["bulk"]["SiW"][1]
    else:
        src = "A" if a.diode == "B" and a.mesh == "A" else a.diode
        g = ise_grid.load(os.path.join(ISE, "s%s_msh.grd" % src), os.path.join(ISE, "s%s_msh.dat" % src))
        if src != a.diode:
            # анод B — правая половина анода A: линия x = 0.5 на сетке A — линия узлов,
            # ни один треугольник анода её не пересекает (проверено), так что вырезается точно
            mat, tri = g["contacts"]["Anode"]
            keep = g["vertices"][tri][:, :, 0].min(axis=1) >= 0.5 - 1e-9
            g["contacts"]["Anode"] = (mat, tri[keep])
            print("анод B вырезан из сетки A: %d треугольников из %d" % (keep.sum(), len(tri)), flush=True)
        if a.lz != 0.8:
            # сетка ISE по варианту 2 — это сетка методички, сжатая по z в 2/0.8 = 2.5 раза;
            # масштабирование сетки ISE по z под другую толщину
            g["vertices"] = g["vertices"] * np.array([1.0, 1.0, a.lz / 0.8])
            print("сетка растянута по z до толщины %g мкм" % a.lz, flush=True)
        print("сетка ISE (%s): %d узлов" % (src, len(g["vertices"])), flush=True)
        dev_ise.create_device(dev_ise.mesh_from_ise(g), g["donors"], g["acceptors"])
        verts, tets = g["vertices"], list(g["bulk"].values())[0][1]
    if a.box != "devsim":
        print("ячейки: %s" % dev_ise.correct_box(verts, tets, a.box), flush=True)
    dev_ise.setup(field_dependent=not a.no_hfs)
    print("равновесие: %.0f с, память %.0f МБ, n_i=%g" % (time.time() - t0, peak_mb(), dev_ise.NI), flush=True)
    iv = dev_ise.ramp(a.vmax, a.step, a.maxstep, log=lambda s: print(s, flush=True))
    where = ("gmsh%g" % a.gmsh if a.gmsh else "tensor%d" % a.tensor if a.tensor
             else ("isemeshA" if a.diode == "B" and a.mesh == "A" else "isemesh"))
    where += "" if a.lz == 0.8 else "_lz%g" % a.lz
    where += "" if a.box == "devsim" else "_" + a.box
    out = os.path.join(HERE, "iv_ise_%s_%s%s.json" % (a.diode, where, a.tag))
    json.dump(iv, open(out, "w"))
    elem = dev_ise.HFS_DRIVE == "elem" and not a.no_hfs
    dev3d.save_fields(out.replace("iv_ise_", "field_ise_").replace(".json", ".npz"),
                      dev_ise.DEV, dev_ise.REG, "element" if elem else "edge")
    print("готово за %.0f с, пиковая память %.0f МБ, ВАХ в %s" % (time.time() - t0, peak_mb(), out), flush=True)

    compare(a.diode, iv)


def compare(diode, iv):
    """Таблица: наш расчёт против ISE (наш прогон, ise/s<диод>_des.plt) и эталона преподавателя."""
    import viz

    def at(V, I, v):
        return np.exp(np.interp(v, V, np.log(np.maximum(np.abs(I), 1e-30)))) if v <= V.max() + 1e-9 else np.nan

    V, I = np.array(iv).T
    plt = os.path.join(ISE, "s%s_des.plt" % diode)
    Vi = Ii = np.array([0.0])
    if os.path.exists(plt):
        d = viz.read_plt(plt)
        Vi, Ii = np.asarray(d["Anode OuterVoltage"]), np.abs(np.asarray(d["Anode TotalCurrent"]))
    ref = json.load(open(os.path.join(HERE, "reference_iv.json")))[diode]
    Vr, Ir = np.array(ref[0]), np.array(ref[1])
    print("\n   V      наш, А     ISE, А    наш/ISE   эталон, А  наш/эталон")
    for v in (0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 3.95):
        i, i1 = at(V, I, v), at(Vi, Ii, v)
        i2 = np.interp(v, Vr, Ir) if v >= 0.9 else np.nan     # с картинки читается только выше ~0.9 В
        print("  %.2f  %10.4e  %10.4e  %7.4f  %10.4e  %7.4f" % (v, i, i1, i / i1, i2, i / i2))
    # в собственных точках ISE (без интерполяции на его стороне): на изломе обе ВАХ
    # идут с шагом 0.1–0.2 В, и логарифмическая интерполяция там врёт на десятки процентов
    sel = (Vi > 0.25) & (Vi <= V.max() + 1e-9)
    if sel.any():
        r = np.array([at(V, I, v) for v in Vi[sel]]) / Ii[sel]
        print("\n  в точках ISE: " + "  ".join("%.2f:%.3f" % (v, x) for v, x in zip(Vi[sel], r)))


if __name__ == "__main__":
    main()
