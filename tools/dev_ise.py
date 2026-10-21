# -*- coding: utf-8 -*-
"""DEVSIM с физикой из командного файла ISE (Lab3_diode_3D/ise/sA_des.cmd).

    Physics {
        Mobility( DopingDep HighFieldsat Enormal )
        EffectiveIntrinsicDensity(BandGapNarrowing (OldSlotboom))
    }

Что это значит в dessis по умолчанию и как сделано здесь:
  DopingDep    — модель Масетти по полному легированию N = N_D + N_A, параметры dessis для Si;
  HighFieldsat — модель Канали; движущая сила у ISE 7 — модуль поля на элементе (проверено по
                 его же подвижностям в узлах, experiments/ise_physics/), не градиент квазиуровня:
                 mu = mu_low / (1 + (mu_low·F/vsat)^beta)^(1/beta),
                 vsat = 1.07e7 / 8.37e6 см/с, beta = 1.109 / 1.213 (электроны / дырки, 300 К);
  OldSlotboom  — сужение зоны dEg = 9 мэВ·(ln(N/1e17) + sqrt(ln²(N/1e17) + 0.5)),
                 пополам в зону проводимости и в валентную: n_ie = n_i·exp(dEg / 2V_t);
  Enormal      — Ломбарди, у поверхности раздела с диэлектриком; диэлектрика в приборе нет,
                 здесь не сделано (ENORMAL — заглушка на будущее);
  рекомбинации в файле ISE нет — нет и здесь.
Схема — та же, что у ISE NewDiscretization: контрольные объёмы на тетраэдрах,
потоки Шарфеттера-Гуммеля. Сетка и легирование могут браться прямо из файлов ISE.

Все размеры — в сантиметрах, напряжения — в вольтах.
"""
import time
import numpy as np
import devsim as ds
from devsim.python_packages.model_create import (
    CreateSolution, CreateNodeModel, CreateNodeModelDerivative,
    CreateEdgeModel, CreateEdgeModelDerivatives, CreateContactNodeModel)

DEV, REG = "diode", "si"
CONTACTS = ("anode", "cathode")
T = 300.0
Q = 1.602176634e-19
VT = 1.380649e-23 * T / Q
EPS = 11.7 * 8.8541878128e-14
NI = 1.4385e10                    # калибровка по ВАХ ISE на его же сетке: при малых смещениях ток ~ n_i²,
                                  # отношение к ISE постоянно от 0.1 до 0.5 В; при n_i = 1.359e10 и
                                  # исправленных ячейках (BOX="clip") оно 0.8925 -> 1.359e10/sqrt(0.8925)
HFS_DRIVE = "elem"                # движущая сила насыщения: "elem" — |E| на тетраэдре (как у ISE: его
                                  # подвижности в sA_des.dat — Канали от полного |E|), "e" — проекция поля
                                  # на ребро (на сетке эталона ток на 3–4 % выше ISE), "qf" — градиент
                                  # квазиуровня (излом ВАХ вдвое выше ISE, наклон при малых токах n = 1.03).
                                  # С "elem" на сетке эталона: 0.966–0.990 (A) и 0.966–0.996 (B) от ISE
                                  # в его собственных точках на 0.4–4 В
LOW_RELERR = 1e-5                 # допуск ниже EXT_BELOW, если float128 выключен (мелкие сетки, --fast)
EXT_BELOW = 0.7                  # float128 в сборке нужен, пока ток мал; выше — обычный double
F_SMOOTH = 1.0                    # В/см: |F| = sqrt(F² + F_SMOOTH²), гладко в нуле

MASETTI = {   # mu_min1, mu_min2, mu1, Pc, Cr, Cs, alpha, beta, mu_const — Si, dessis
    "n": (52.2, 52.2, 43.4, 0.0, 9.68e16, 3.43e20, 0.680, 2.0, 1417.0),
    "p": (44.9, 0.0, 29.0, 9.23e16, 2.23e17, 6.10e20, 0.719, 2.0, 470.5),
}
CANALI = {"n": (1.07e7, 1.109), "p": (8.37e6, 1.213)}   # vsat, beta при 300 К
SLOTBOOM_OLD = (9.0e-3, 1.0e17, 0.5)                    # E_bgn (эВ), N_ref, C

SOLVER = "direct"
RELERR = 1e-8


def masetti(kind):
    m1, m2, mu1, pc, cr, cs, a, b, mc = MASETTI[kind]
    first = "%g*exp(-%g/NTotal)" % (m1, pc) if pc > 0 else "%g" % m1
    return "%s + %g/(1 + pow(NTotal/%g, %g)) - %g/(1 + pow(%g/NTotal, %g))" % (
        first, mc - m2, cr, a, mu1, cs, b)


# ------------------------------------------------------------------- сетка
def mesh_from_ise(grid, mesh="m"):
    """Сетка из tools/ise_grid.load(): координаты мкм -> см."""
    v = grid["vertices"] * 1e-4
    names = ["silicon", "anode", "cathode"]
    el = []
    (_, tets), = grid["bulk"].values()
    for t in tets:
        el += [3, 0, *t]
    for name, idx in (("Anode", 1), ("Cathode", 2)):
        for t in grid["contacts"][name][1]:
            el += [2, idx, *t]
    ds.create_gmsh_mesh(mesh=mesh, coordinates=v.ravel().tolist(), elements=[int(e) for e in el],
                        physical_names=names)
    return mesh


def create_device(mesh, donors=None, acceptors=None, junction=None):
    """Прибор из сетки. Легирование — массивами по узлам (как в ISE) либо ступенькой по z."""
    ds.add_gmsh_region(gmsh_name="silicon", mesh=mesh, region=REG, material="Silicon")
    for c in CONTACTS:
        ds.add_gmsh_contact(gmsh_name=c, region=REG, name=c, mesh=mesh, material="metal")
    ds.finalize_mesh(mesh=mesh)
    ds.create_device(mesh=mesh, device=DEV)
    for name, val in (("Donors", donors), ("Acceptors", acceptors)):
        if val is not None:
            ds.node_solution(device=DEV, region=REG, name=name)
            ds.set_node_values(device=DEV, region=REG, name=name, values=list(map(float, val)))
    if donors is None:
        NA, ND, zj = junction
        CreateNodeModel(DEV, REG, "Acceptors", "%g*step(z-%g)" % (NA, zj))
        CreateNodeModel(DEV, REG, "Donors", "%g*step(%g-z)" % (ND, zj))


# ------------------------------------------------------------------- геометрия ячеек
BOX = "clip"     # "devsim" — как есть; "signed" — грани Вороного со знаком; "clip" — со знаком, < 0 -> 0.
                 # На сетке ISE signed и clip совпадают (отрицательные — шум ~1e-17 мкм²), а с ними
                 # ВАХ A на 1.5–4 В в пределах 2 % от ISE; с ячейками DEVSIM — на 10–15 % выше


def correct_box(verts_um, tets, mode=None):
    """Поправить площади граней ячеек и объёмы, которые DEVSIM 2.11 завышает в 3D.

    DEVSIM складывает вклады тетраэдров в грань Вороного по модулю: на сетке ISE диода A
    сумма объёмов ячеек 3.06 мкм³ вместо 2.4. Встроенную EdgeCouple не заменить, поэтому
    все рёберные потоки домножаются на CR = площадь_правильная / EdgeCouple, а узловые
    заряды — на VR = объём_правильный / NodeVolume (модели CR и VR, см. _flux и _charge).
    """
    import voronoi3d
    mode = mode or BOX
    nodes = len(ds.get_node_model_values(device=DEV, region=REG, name="x"))
    ds.node_solution(device=DEV, region=REG, name="nid")
    ds.set_node_values(device=DEV, region=REG, name="nid", values=[float(i) for i in range(nodes)])
    ds.edge_from_node_model(device=DEV, region=REG, node_model="nid")
    xyz = np.stack([ds.get_node_model_values(device=DEV, region=REG, name=k) for k in "xyz"], axis=1) * 1e4
    # узлы DEVSIM -> наши вершины (по координатам, мкм)
    key = {tuple(np.round(p, 7)): i for i, p in enumerate(verts_um)}
    d2v = np.array([key[tuple(np.round(p, 7))] for p in xyz])
    v2d = np.empty_like(d2v); v2d[d2v] = np.arange(len(d2v))
    e0 = np.array(ds.get_edge_model_values(device=DEV, region=REG, name="nid@n0")).astype(int)
    e1 = np.array(ds.get_edge_model_values(device=DEV, region=REG, name="nid@n1")).astype(int)

    edges, signed, _ = voronoi3d.couples(verts_um, tets)
    area = signed if mode == "signed" else np.maximum(signed, 0.0)
    if mode == "devsim":
        area = None
    ec = np.array(ds.get_edge_model_values(device=DEV, region=REG, name="EdgeCouple"))
    el = np.array(ds.get_edge_model_values(device=DEV, region=REG, name="EdgeLength"))
    nv = np.array(ds.get_node_model_values(device=DEV, region=REG, name="NodeVolume"))
    if area is None:
        cr, vr = np.ones_like(ec), np.ones_like(nv)
    else:
        a, b = d2v[e0], d2v[e1]
        lo, hi = np.minimum(a, b), np.maximum(a, b)
        idx = {(int(p), int(q)): k for k, (p, q) in enumerate(edges)}
        mine = np.array([area[idx[(int(p), int(q))]] for p, q in zip(lo, hi)]) * 1e-8   # мкм² -> см²
        zero = ec == 0
        cr = np.where(zero, 0.0, mine / np.where(zero, 1.0, ec))
        if zero.any():   # DEVSIM не даёт этому ребру потока — поправить нечем
            print("  correct_box: рёбер с EdgeCouple=0 у DEVSIM: %d, наша площадь там: макс %.3g мкм²"
                  % (zero.sum(), np.abs(mine[zero]).max() * 1e8), flush=True)
        # объём ячейки: пирамиды A·(L/2)/3 от каждого ребра к обоим его концам
        vol = np.zeros(nodes)
        np.add.at(vol, e0, mine * el / 6); np.add.at(vol, e1, mine * el / 6)
        vr = vol / nv
    ds.edge_solution(device=DEV, region=REG, name="CR")
    ds.set_edge_values(device=DEV, region=REG, name="CR", values=cr.tolist())
    ds.node_solution(device=DEV, region=REG, name="VR")
    ds.set_node_values(device=DEV, region=REG, name="VR", values=vr.tolist())
    return {"mode": mode, "volume_um3": float((nv * vr).sum() * 1e12),
            "negative_edges": int((cr < 0).sum()), "edges": len(cr)}


# ------------------------------------------------------------------- физика
def parameters():
    for name, val in (("Permittivity", EPS), ("ElectronCharge", Q), ("V_t", VT), ("n_i", NI)):
        ds.set_parameter(device=DEV, region=REG, name=name, value=val)
    for c in CONTACTS:
        ds.set_parameter(device=DEV, name=c + "_bias", value=0.0)


def doping_models():
    E, Nref, C = SLOTBOOM_OLD
    CreateNodeModel(DEV, REG, "NetDoping", "Donors-Acceptors")
    CreateNodeModel(DEV, REG, "NTotal", "Donors+Acceptors")
    CreateNodeModel(DEV, REG, "dEg", "%g*(log(NTotal/%g) + pow(log(NTotal/%g)^2 + %g, 0.5))"
                    % (E, Nref, Nref, C))
    CreateNodeModel(DEV, REG, "n_ie", "n_i*exp(dEg/(2*V_t))")
    for k in ("n", "p"):
        CreateNodeModel(DEV, REG, "mulow_" + k, masetti(k))
    for m in ("dEg", "mulow_n", "mulow_p"):
        ds.edge_from_node_model(device=DEV, region=REG, node_model=m)
    # равновесные концентрации на контактах (электронейтральность, n·p = n_ie²)
    CreateNodeModel(DEV, REG, "celec", "0.5*(NetDoping + pow(NetDoping^2 + 4*n_ie^2, 0.5))")
    CreateNodeModel(DEV, REG, "chole", "0.5*(-NetDoping + pow(NetDoping^2 + 4*n_ie^2, 0.5))")


def poisson_only():
    CreateSolution(DEV, REG, "Potential")
    for n, e in (("IntrinsicElectrons", "n_ie*exp(Potential/V_t)"),
                 ("IntrinsicHoles", "n_ie^2/IntrinsicElectrons"),
                 ("PotentialIntrinsicCharge", "-VR*ElectronCharge*kahan3(IntrinsicHoles, -IntrinsicElectrons, NetDoping)")):
        CreateNodeModel(DEV, REG, n, e)
        CreateNodeModelDerivative(DEV, REG, n, e, "Potential")
    for n, e in (("ElectricField", "(Potential@n0-Potential@n1)*EdgeInverseLength"),
                 ("PotentialEdgeFlux", "CR*Permittivity*ElectricField")):
        CreateEdgeModel(DEV, REG, n, e)
        CreateEdgeModelDerivatives(DEV, REG, n, e, "Potential")
    ds.equation(device=DEV, region=REG, name="PotentialEquation", variable_name="Potential",
                node_model="PotentialIntrinsicCharge", edge_model="PotentialEdgeFlux",
                variable_update="log_damp")
    for c in CONTACTS:
        m = "Potential - %s_bias - ifelse(NetDoping > 0, V_t*log(celec/n_ie), -V_t*log(chole/n_ie))" % c
        CreateContactNodeModel(DEV, c, c + "_pot", m)
        CreateContactNodeModel(DEV, c, c + "_pot:Potential", "1")
        ds.contact_equation(device=DEV, contact=c, name="PotentialEquation",
                            node_model=c + "_pot", edge_charge_model="PotentialEdgeFlux")


def _edge(name, expr, variables):
    CreateEdgeModel(DEV, REG, name, expr)
    for v in variables:
        CreateEdgeModelDerivatives(DEV, REG, name, expr, v)


def drift_diffusion(field_dependent=True):
    CreateSolution(DEV, REG, "Electrons")
    CreateSolution(DEV, REG, "Holes")
    ds.set_node_values(device=DEV, region=REG, name="Electrons", init_from="IntrinsicElectrons")
    ds.set_node_values(device=DEV, region=REG, name="Holes", init_from="IntrinsicHoles")
    sol = ("Potential", "Electrons", "Holes")

    pne = "-VR*ElectronCharge*kahan3(Holes, -Electrons, NetDoping)"
    CreateNodeModel(DEV, REG, "PotentialNodeCharge", pne)
    for v in ("Electrons", "Holes"):
        CreateNodeModelDerivative(DEV, REG, "PotentialNodeCharge", pne, v)
    ds.equation(device=DEV, region=REG, name="PotentialEquation", variable_name="Potential",
                node_model="PotentialNodeCharge", edge_model="PotentialEdgeFlux",
                variable_update="log_damp")

    # зоны сдвинуты на ±dEg/2: электроны видят Potential + dEg/2, дырки — Potential - dEg/2
    _edge("vdn", "(Potential@n0 - Potential@n1 + 0.5*(dEg@n0 - dEg@n1))/V_t", ["Potential"])
    _edge("vdp", "(Potential@n0 - Potential@n1 - 0.5*(dEg@n0 - dEg@n1))/V_t", ["Potential"])
    for k in ("n", "p"):
        _edge("mul_" + k, "0.5*(mulow_%s@n0 + mulow_%s@n1)" % (k, k), [])
        if field_dependent:
            vsat, beta = CANALI[k]
            if HFS_DRIVE == "e":   # поле вдоль ребра
                dphi = "(Potential@n1 - Potential@n0)"
            elif k == "n":         # квазиуровень электронов phi_n = Potential + dEg/2 - V_t·ln(n/n_i)
                dphi = "(Potential@n1 - Potential@n0 + 0.5*(dEg@n1 - dEg@n0) - V_t*log(Electrons@n1/Electrons@n0))"
            else:                  # дырок phi_p = Potential - dEg/2 + V_t·ln(p/n_i)
                dphi = "(Potential@n1 - Potential@n0 - 0.5*(dEg@n1 - dEg@n0) + V_t*log(Holes@n1/Holes@n0))"
            _edge("F_" + k, "pow((%s*EdgeInverseLength)^2 + %g, 0.5)" % (dphi, F_SMOOTH ** 2), sol)
            _edge("mu_" + k, "mul_{k}*pow(1 + pow(mul_{k}*F_{k}/{v:g}, {b:g}), {ib:.12g})".format(
                k=k, v=vsat, b=beta, ib=-1.0 / beta), sol)
        else:
            _edge("mu_" + k, "mul_" + k, [])

    Jn = "CR*ElectronCharge*mu_n*EdgeInverseLength*V_t*kahan3(Electrons@n1*B(vdn), Electrons@n1*vdn, -Electrons@n0*B(vdn))"
    Jp = "-CR*ElectronCharge*mu_p*EdgeInverseLength*V_t*kahan3(Holes@n1*B(vdp), -Holes@n0*B(vdp), -Holes@n0*vdp)"
    _edge("ElectronCurrent", Jn, sol)
    _edge("HoleCurrent", Jp, sol)
    for n, e, v in (("NCharge", "-ElectronCharge*Electrons", "Electrons"),
                    ("PCharge", "ElectronCharge*Holes", "Holes")):
        CreateNodeModel(DEV, REG, n, e)
        CreateNodeModelDerivative(DEV, REG, n, e, v)
    elem = field_dependent and HFS_DRIVE == "elem"
    if elem:
        element_currents(Jn, Jp)
    kw = (lambda k: {"element_model": k + "Elem"}) if elem else (lambda k: {"edge_model": k})
    ds.equation(device=DEV, region=REG, name="ElectronContinuityEquation", variable_name="Electrons",
                time_node_model="NCharge", variable_update="positive", **kw("ElectronCurrent"))
    ds.equation(device=DEV, region=REG, name="HoleContinuityEquation", variable_name="Holes",
                time_node_model="PCharge", variable_update="positive", **kw("HoleCurrent"))
    ckw = (lambda k: {"element_current_model": k + "Elem"}) if elem else (lambda k: {"edge_current_model": k})
    for c in CONTACTS:
        CreateContactNodeModel(DEV, c, c + "_n", "Electrons - ifelse(NetDoping > 0, celec, n_ie^2/chole)")
        CreateContactNodeModel(DEV, c, c + "_n:Electrons", "1")
        CreateContactNodeModel(DEV, c, c + "_p", "Holes - ifelse(NetDoping < 0, chole, n_ie^2/celec)")
        CreateContactNodeModel(DEV, c, c + "_p:Holes", "1")
        ds.contact_equation(device=DEV, contact=c, name="ElectronContinuityEquation",
                            node_model=c + "_n", **ckw("ElectronCurrent"))
        ds.contact_equation(device=DEV, contact=c, name="HoleContinuityEquation",
                            node_model=c + "_p", **ckw("HoleCurrent"))


EN = ("@en0", "@en1", "@en2", "@en3")       # узлы тетраэдра в элементных моделях DEVSIM


def _elem(name, expr, variables=()):
    ds.element_model(device=DEV, region=REG, name=name, equation=expr)
    for v in variables:
        for e in EN:
            ds.element_model(device=DEV, region=REG, name="%s:%s%s" % (name, v, e),
                             equation="diff(%s, %s%s)" % (expr, v, e))


def element_currents(Jn_edge, Jp_edge):
    """Насыщение по модулю поля на тетраэдре (HFS_DRIVE = "elem"), как у ISE.

    Подвижности, которые ISE пишет в sA_des.dat, — это Канали от полного |E|: медиана
    отношения к формуле ровно 1.00 (experiments/ise_physics/drive_probe.py). На ребре видна
    только проекция поля — на косых рёбрах она меньше |E|, подвижность выше, ток на
    сетке эталона на 3–4 % выше ISE. Здесь вектор поля собирается на каждом тетраэдре
    из его рёбер, подвижность — на элементе, поток Шарфеттера-Гуммеля — тот же, но
    элементной моделью (как dev3d.element_currents, по образцу mos_physics.py DEVSIM).
    Поправка ячеек CR — рёберная: все вклады ребра масштабируются одинаково.
    """
    ds.element_from_edge_model(edge_model="ElectricField", device=DEV, region=REG)
    ds.element_from_edge_model(edge_model="ElectricField", device=DEV, region=REG, derivative="Potential")
    ds.element_model(device=DEV, region=REG, name="Emag",
                     equation="pow(ElectricField_x^2 + ElectricField_y^2 + ElectricField_z^2 + %g, 0.5)"
                     % F_SMOOTH ** 2)
    for e in EN:
        ds.element_model(device=DEV, region=REG, name="Emag:Potential" + e, equation=(
            "(ElectricField_x*ElectricField_x:Potential{0} + ElectricField_y*ElectricField_y:Potential{0}"
            " + ElectricField_z*ElectricField_z:Potential{0})/Emag").format(e))
    for k in ("n", "p"):
        vsat, beta = CANALI[k]
        _elem("mu_%s_elem" % k, "mul_{k}*pow(1 + pow(mul_{k}*Emag/{v:g}, {b:g}), {ib:.12g})".format(
            k=k, v=vsat, b=beta, ib=-1.0 / beta), ("Potential",))
    sol = ("Potential", "Electrons", "Holes")
    for name, J, k in (("ElectronCurrentElem", Jn_edge, "n"), ("HoleCurrentElem", Jp_edge, "p")):
        J = J.replace("mu_%s*" % k, "mu_%s_elem*" % k).replace("@n0", "@en0").replace("@n1", "@en1")
        _elem(name, J, sol)


# ------------------------------------------------------------------- счёт
def solve(rel=None, iters=40):
    ds.solve(type="dc", solver_type=SOLVER, absolute_error=1e10,
             relative_error=rel or RELERR, maximum_iterations=iters)


def extended(on):
    for p in ("extended_model", "extended_equation"):
        ds.set_parameter(name=p, value=bool(on))


FAST = False   # мелкие сетки: без float128; ниже EXT_BELOW допуск LOW_RELERR (ток там ничтожен)


def setup(field_dependent=True):
    extended(not FAST)
    if "CR" not in ds.get_edge_model_list(device=DEV, region=REG):     # без correct_box — как есть
        CreateEdgeModel(DEV, REG, "CR", "1")
        CreateNodeModel(DEV, REG, "VR", "1")
    parameters()
    doping_models()
    poisson_only()
    ds.solve(type="dc", solver_type=SOLVER, absolute_error=1.0,
             relative_error=1e-10 if FAST else 1e-12, maximum_iterations=60)
    drift_diffusion(field_dependent)
    solve(rel=LOW_RELERR if FAST else None)


def anode_current():
    return sum(ds.get_contact_current(device=DEV, contact="anode", equation=e)
               for e in ("ElectronContinuityEquation", "HoleContinuityEquation"))


SOL = ("Potential", "Electrons", "Holes")


def _snapshot():
    return {s: np.array(ds.get_node_model_values(device=DEV, region=REG, name=s)) for s in SOL}


def _restore(x):
    for s in SOL:
        ds.set_node_values(device=DEV, region=REG, name=s, values=x[s].tolist())


def _extrapolate(cur, prev, r):
    """Начальное приближение для нового напряжения, как Extrapolate у ISE:
    потенциал — линейно по V, концентрации — линейно в логарифме (они ~ exp(V/V_t))."""
    out = {"Potential": cur["Potential"] + r * (cur["Potential"] - prev["Potential"])}
    for s in ("Electrons", "Holes"):
        # не больше e^3 ≈ 20 раз за шаг: на изломе рост тока резко замедляется, и полный
        # логарифмический прогноз (×500 за 0.2 В) уводит концентрации к 1e20 — Ньютон вязнет
        out[s] = cur[s] * np.exp(np.clip(r * np.log(cur[s] / prev[s]), -3, 3))
    return out


def ramp(vmax=4.0, step=0.1, maxstep=0.2, log=print, extrapolate=True):
    """Развёртка анода, как Quasistationary у ISE: шаг растёт в 1.5 раза до maxstep
    (MaxStep=0.05 от 4 В = 0.2 В), при срыве делится пополам. Возвращает [(V, I)]."""
    V, out, t0, h = 0.0, [(0.0, anode_current())], time.time(), step
    ext, ext_below = not FAST, EXT_BELOW
    cur, prev, Vprev = _snapshot(), None, None
    while V < vmax - 1e-9:
        if ext and V >= ext_below - 1e-9:
            extended(False); ext = False
        Vn = min(V + h, vmax)
        ds.set_parameter(device=DEV, name="anode_bias", value=Vn)
        if extrapolate and prev is not None:
            _restore(_extrapolate(cur, prev, (Vn - V) / (V - Vprev)))
        try:
            solve(rel=LOW_RELERR if FAST and Vn < EXT_BELOW - 1e-9 else None, iters=30)
        except ds.error:
            ds.set_parameter(device=DEV, name="anode_bias", value=V)
            _restore(cur)
            if not ext:                      # тот же шаг во float128 — и так уже до конца
                extended(True); ext, ext_below = True, float("inf")
                log("  %.3f В: в double не сошлось, дальше float128" % Vn)
                continue
            h /= 2
            if h < 1e-4:
                log("  не сходится у %.4f В, останавливаюсь" % V); break
            continue
        Vprev, V = V, Vn
        prev, cur = cur, _snapshot()
        out.append((V, anode_current()))
        log("  V=%.3f  I=%.5e А  %s (%.0f с)" % (V, out[-1][1], "f128" if ext else "f64 ", time.time() - t0))
        h = min(maxstep, h * 1.5)
    return out
