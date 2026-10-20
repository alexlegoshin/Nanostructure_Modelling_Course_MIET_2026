# -*- coding: utf-8 -*-
"""DEVSIM с физикой из командного файла ISE (Lab3_diode_3D/ise/sA_des.cmd).

    Physics {
        Mobility( DopingDep HighFieldsat Enormal )
        EffectiveIntrinsicDensity(BandGapNarrowing (OldSlotboom))
    }

Что это значит в dessis по умолчанию и как сделано здесь:
  DopingDep    — модель Масетти по полному легированию N = N_D + N_A, параметры dessis для Si;
  HighFieldsat — модель Канали, движущая сила — градиент квазиуровня Ферми (GradQuasiFermi):
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
NI = 1.416e10                     # калибровка по ВАХ ISE: при n_i = 1e10 ток A при 0.1 В вдвое ниже ISE
                                  # (1.278e-16 против 2.549e-16 А), ток ~ n_i² -> 1e10·sqrt(1.994)
EXT_BELOW = 0.7                   # float128 в сборке нужен, пока ток мал; выше — обычный double
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
                 ("PotentialIntrinsicCharge", "-ElectronCharge*kahan3(IntrinsicHoles, -IntrinsicElectrons, NetDoping)")):
        CreateNodeModel(DEV, REG, n, e)
        CreateNodeModelDerivative(DEV, REG, n, e, "Potential")
    for n, e in (("ElectricField", "(Potential@n0-Potential@n1)*EdgeInverseLength"),
                 ("PotentialEdgeFlux", "Permittivity*ElectricField")):
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

    pne = "-ElectronCharge*kahan3(Holes, -Electrons, NetDoping)"
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
            if k == "n":   # квазиуровень электронов phi_n = Potential + dEg/2 - V_t·ln(n/n_i)
                dphi = "(Potential@n1 - Potential@n0 + 0.5*(dEg@n1 - dEg@n0) - V_t*log(Electrons@n1/Electrons@n0))"
            else:          # дырок phi_p = Potential - dEg/2 + V_t·ln(p/n_i)
                dphi = "(Potential@n1 - Potential@n0 - 0.5*(dEg@n1 - dEg@n0) + V_t*log(Holes@n1/Holes@n0))"
            _edge("F_" + k, "pow((%s*EdgeInverseLength)^2 + %g, 0.5)" % (dphi, F_SMOOTH ** 2), sol)
            _edge("mu_" + k, "mul_{k}*pow(1 + pow(mul_{k}*F_{k}/{v:g}, {b:g}), {ib:.12g})".format(
                k=k, v=vsat, b=beta, ib=-1.0 / beta), sol)
        else:
            _edge("mu_" + k, "mul_" + k, [])

    Jn = "ElectronCharge*mu_n*EdgeInverseLength*V_t*kahan3(Electrons@n1*B(vdn), Electrons@n1*vdn, -Electrons@n0*B(vdn))"
    Jp = "-ElectronCharge*mu_p*EdgeInverseLength*V_t*kahan3(Holes@n1*B(vdp), -Holes@n0*B(vdp), -Holes@n0*vdp)"
    _edge("ElectronCurrent", Jn, sol)
    _edge("HoleCurrent", Jp, sol)
    for n, e, v in (("NCharge", "-ElectronCharge*Electrons", "Electrons"),
                    ("PCharge", "ElectronCharge*Holes", "Holes")):
        CreateNodeModel(DEV, REG, n, e)
        CreateNodeModelDerivative(DEV, REG, n, e, v)
    ds.equation(device=DEV, region=REG, name="ElectronContinuityEquation", variable_name="Electrons",
                time_node_model="NCharge", edge_model="ElectronCurrent", variable_update="positive")
    ds.equation(device=DEV, region=REG, name="HoleContinuityEquation", variable_name="Holes",
                time_node_model="PCharge", edge_model="HoleCurrent", variable_update="positive")
    for c in CONTACTS:
        CreateContactNodeModel(DEV, c, c + "_n", "Electrons - ifelse(NetDoping > 0, celec, n_ie^2/chole)")
        CreateContactNodeModel(DEV, c, c + "_n:Electrons", "1")
        CreateContactNodeModel(DEV, c, c + "_p", "Holes - ifelse(NetDoping < 0, chole, n_ie^2/celec)")
        CreateContactNodeModel(DEV, c, c + "_p:Holes", "1")
        ds.contact_equation(device=DEV, contact=c, name="ElectronContinuityEquation",
                            node_model=c + "_n", edge_current_model="ElectronCurrent")
        ds.contact_equation(device=DEV, contact=c, name="HoleContinuityEquation",
                            node_model=c + "_p", edge_current_model="HoleCurrent")


# ------------------------------------------------------------------- счёт
def solve(rel=None, iters=40):
    ds.solve(type="dc", solver_type=SOLVER, absolute_error=1e10,
             relative_error=rel or RELERR, maximum_iterations=iters)


def extended(on):
    for p in ("extended_model", "extended_equation"):
        ds.set_parameter(name=p, value=bool(on))


def setup(field_dependent=True):
    extended(True)
    parameters()
    doping_models()
    poisson_only()
    ds.solve(type="dc", solver_type=SOLVER, absolute_error=1.0, relative_error=1e-12, maximum_iterations=60)
    drift_diffusion(field_dependent)
    solve()


def anode_current():
    return sum(ds.get_contact_current(device=DEV, contact="anode", equation=e)
               for e in ("ElectronContinuityEquation", "HoleContinuityEquation"))


def ramp(vmax=4.0, step=0.1, maxstep=0.2, log=print):
    """Развёртка анода, как Quasistationary у ISE: шаг растёт в 1.5 раза до maxstep
    (MaxStep=0.05 от 4 В = 0.2 В), при срыве делится пополам. Возвращает [(V, I)]."""
    V, out, t0, h = 0.0, [(0.0, anode_current())], time.time(), step
    ext, ext_below = True, EXT_BELOW
    while V < vmax - 1e-9:
        if ext and V >= ext_below - 1e-9:
            extended(False); ext = False
        Vn = min(V + h, vmax)
        ds.set_parameter(device=DEV, name="anode_bias", value=Vn)
        try:
            solve(iters=30)
        except ds.error:
            ds.set_parameter(device=DEV, name="anode_bias", value=V)
            if not ext:                      # тот же шаг во float128 — и так уже до конца
                extended(True); ext, ext_below = True, float("inf")
                log("  %.3f В: в double не сошлось, дальше float128" % Vn)
                continue
            h /= 2
            if h < 1e-4:
                log("  не сходится у %.4f В, останавливаюсь" % V); break
            continue
        V = Vn
        out.append((V, anode_current()))
        log("  V=%.3f  I=%.5e А  %s (%.0f с)" % (V, out[-1][1], "f128" if ext else "f64 ", time.time() - t0))
        h = min(maxstep, h * 1.5)
    return out
