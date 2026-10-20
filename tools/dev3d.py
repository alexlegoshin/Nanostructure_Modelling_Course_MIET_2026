# -*- coding: utf-8 -*-
"""3D-диод в DEVSIM: загрузка сетки Gmsh, легирование, равновесие, развёртка.

Подвижность — та же, что в своём решателе (dd3d.py): Коги-Томас по легированию
и насыщение скорости по полю вдоль ребра. Стандартный simple_physics берёт
постоянные 400/200 см2/(В*с), и ток при 4 В выходит вчетверо больше, чем у ISE.
"""

import devsim as ds
from devsim.python_packages.simple_physics import (
    SetSiliconParameters, CreateSiliconPotentialOnly, CreateSiliconPotentialOnlyContact,
    CreateSiliconDriftDiffusion, CreateSiliconDriftDiffusionAtContact, GetContactBiasName)
from devsim.python_packages.model_create import CreateSolution, CreateNodeModel

NA, ND, LZ = 1.4e17, 1.0e17, 0.8e-4
DEV, REG = "diode", "si"
SOLVER = "direct"           # "iterative" (GMRES) экономит память, но под смещением врёт
RELERR = 1e-8               # на грубых 3D-сетках Ньютон застревает около 1e-5 — тогда ослабить
CONTACTS = ("anode", "cathode")
MOBILITY = "element"        # "element" — насыщение по полному |E| на тетраэдре (по умолчанию),
                            # "field" — по проекции поля на ребро, "constant" — 400/200 из simple_physics
VSAT = 1.07e7               # см/с
# Коги-Томас: mu_min, mu_max, N_ref, alpha — те же числа, что в dd3d.mu_doping
CT = {"n": (68.5, 1414.0, 9.2e16, 0.711), "p": (44.9, 470.5, 2.23e17, 0.719)}
BETA = {"n": 2.0, "p": 1.0}


def mobility_doping(kind):
    """Подвижность по легированию в узлах и её среднее на ребре (edge-модель mu_dop_<kind>_e)."""
    mn, mx, nref, a = CT[kind]
    name = "mu_dop_" + kind
    CreateNodeModel(DEV, REG, name, "%g + %g/(1 + pow(pow(NetDoping^2, 0.5)/%g, %g))"
                    % (mn, mx - mn, nref, a))
    ds.edge_from_node_model(device=DEV, region=REG, node_model=name)
    ds.edge_model(device=DEV, region=REG, name=name + "_e",
                  equation="0.5*(%s@n0 + %s@n1)" % (name, name))
    return name + "_e"


EN = ("@en0", "@en1", "@en2", "@en3")       # узлы тетраэдра в элементных моделях


def _elem(name, expr, variables=()):
    ds.element_model(device=DEV, region=REG, name=name, equation=expr)
    for v in variables:
        for e in EN:
            ds.element_model(device=DEV, region=REG, name="%s:%s%s" % (name, v, e),
                             equation="diff(%s, %s%s)" % (expr, v, e))


def element_currents():
    """Ток на элементах с насыщением скорости по полному полю.

    На ребре видна только проекция поля, а рёбра тетраэдров идут под углом к току —
    насыщение недооценивается, ток завышен. Здесь вектор поля собирается на каждом
    тетраэдре из его рёбер, подвижность берётся от |E|, ток — тот же поток
    Шарфеттера-Гуммеля, но элементной моделью (как mos_physics.py, только в 3D).
    """
    ds.element_from_edge_model(edge_model="ElectricField", device=DEV, region=REG)
    ds.element_from_edge_model(edge_model="ElectricField", device=DEV, region=REG,
                               derivative="Potential")
    ds.element_model(device=DEV, region=REG, name="Emag",
                     equation="pow(ElectricField_x^2 + ElectricField_y^2 + ElectricField_z^2 + 1, 0.5)")
    for e in EN:
        ds.element_model(device=DEV, region=REG, name="Emag:Potential" + e, equation=(
            "(ElectricField_x*ElectricField_x:Potential{0} + ElectricField_y*ElectricField_y:Potential{0}"
            " + ElectricField_z*ElectricField_z:Potential{0})/Emag").format(e))
    for kind in "np":
        mu0 = mobility_doping(kind)
        if BETA[kind] == 2.0:
            mu = "%s/pow(1 + (%s*Emag/%g)^2, 0.5)" % (mu0, mu0, VSAT)
        else:
            mu = "%s/(1 + %s*Emag/%g)" % (mu0, mu0, VSAT)
        _elem("mu_%s_elem" % kind, mu, ("Potential",))
    Jn = ("ElectronCharge*mu_n_elem*EdgeInverseLength*V_t*"
          "kahan3(Electrons@en1*Bern01, Electrons@en1*vdiff, -Electrons@en0*Bern01)")
    Jp = ("-ElectronCharge*mu_p_elem*EdgeInverseLength*V_t*"
          "kahan3(Holes@en1*Bern01, -Holes@en0*Bern01, -Holes@en0*vdiff)")
    _elem("ElectronCurrentElem", Jn, ("Electrons", "Holes", "Potential"))
    _elem("HoleCurrentElem", Jp, ("Electrons", "Holes", "Potential"))
    # те же уравнения непрерывности, но поток берётся с элементов
    ds.equation(device=DEV, region=REG, name="ElectronContinuityEquation", variable_name="Electrons",
                time_node_model="NCharge", node_model="ElectronGeneration",
                element_model="ElectronCurrentElem", variable_update="positive")
    ds.equation(device=DEV, region=REG, name="HoleContinuityEquation", variable_name="Holes",
                time_node_model="PCharge", node_model="HoleGeneration",
                element_model="HoleCurrentElem", variable_update="positive")
    for c in CONTACTS:
        ds.contact_equation(device=DEV, contact=c, name="ElectronContinuityEquation",
                            node_model="%snodeelectrons" % c, element_current_model="ElectronCurrentElem")
        ds.contact_equation(device=DEV, contact=c, name="HoleContinuityEquation",
                            node_model="%snodeholes" % c, element_current_model="HoleCurrentElem")


def mobility_expr(kind):
    """Подвижность на ребре как строка-выражение для DEVSIM.

    Подставляется прямо в формулу тока Шарфеттера-Гуммеля, поэтому производные
    по потенциалу DEVSIM берёт сам, символьно, и Ньютон остаётся точным.
    """
    mn, mx, nref, a = CT[kind]
    name = "mu_dop_" + kind
    CreateNodeModel(DEV, REG, name, "%g + %g/(1 + pow(pow(NetDoping^2, 0.5)/%g, %g))"
                    % (mn, mx - mn, nref, a))
    ds.edge_from_node_model(device=DEV, region=REG, node_model=name)
    mu0 = "(0.5*(%s@n0 + %s@n1))" % (name, name)
    e2 = "(((Potential@n0 - Potential@n1)*EdgeInverseLength)^2)"
    if BETA[kind] == 2.0:
        return "(%s/pow(1 + %s^2*%s/%g, 0.5))" % (mu0, mu0, e2, VSAT ** 2)
    # beta = 1: |E| сглажен на 1 В/см, чтобы производная в нуле поля была конечной
    return "(%s/(1 + %s*pow(%s + 1, 0.5)/%g))" % (mu0, mu0, e2, VSAT)


def load(msh):
    ds.create_gmsh_mesh(mesh="m", file=msh)
    ds.add_gmsh_region(gmsh_name="silicon", mesh="m", region=REG, material="Silicon")
    for c in CONTACTS:
        ds.add_gmsh_contact(gmsh_name=c, region=REG, name=c, mesh="m", material="metal")
    ds.finalize_mesh(mesh="m")
    ds.create_device(mesh="m", device=DEV)
    SetSiliconParameters(DEV, REG, 300.0)
    # резкий переход: сверху бор, снизу мышьяк
    CreateNodeModel(DEV, REG, "Acceptors", "%g*step(z-%g)" % (NA, LZ / 2))
    CreateNodeModel(DEV, REG, "Donors",    "%g*step(%g-z)" % (ND, LZ / 2))
    CreateNodeModel(DEV, REG, "NetDoping", "Donors-Acceptors")


def equilibrium():
    CreateSolution(DEV, REG, "Potential")
    CreateSiliconPotentialOnly(DEV, REG)
    for c in CONTACTS:
        ds.set_parameter(device=DEV, name=GetContactBiasName(c), value=0.0)
        CreateSiliconPotentialOnlyContact(DEV, REG, c)
    ds.solve(type="dc", solver_type=SOLVER, absolute_error=1.0, relative_error=1e-10, maximum_iterations=40)


def drift_diffusion():
    CreateSolution(DEV, REG, "Electrons")
    CreateSolution(DEV, REG, "Holes")
    ds.set_node_values(device=DEV, region=REG, name="Electrons", init_from="IntrinsicElectrons")
    ds.set_node_values(device=DEV, region=REG, name="Holes", init_from="IntrinsicHoles")
    if MOBILITY == "field":
        CreateSiliconDriftDiffusion(DEV, REG, mu_n=mobility_expr("n"), mu_p=mobility_expr("p"))
    else:
        CreateSiliconDriftDiffusion(DEV, REG)
    for c in CONTACTS:
        CreateSiliconDriftDiffusionAtContact(DEV, REG, c)
    if MOBILITY == "element":
        element_currents()
    ds.solve(type="dc", solver_type=SOLVER, absolute_error=1e10, relative_error=RELERR, maximum_iterations=40)


def anode_current():
    e = ds.get_contact_current(device=DEV, contact="anode", equation="ElectronContinuityEquation")
    h = ds.get_contact_current(device=DEV, contact="anode", equation="HoleContinuityEquation")
    return e + h


def ramp(vmax=4.0, step=0.1, log=print):
    """Развёртка анода с продолжением; при срыве шаг делится пополам."""
    import time
    V, out, t0 = 0.0, [(0.0, anode_current())], time.time()
    h = step
    while V < vmax - 1e-9:
        Vn = min(V + h, vmax)
        ds.set_parameter(device=DEV, name=GetContactBiasName("anode"), value=Vn)
        try:
            ds.solve(type="dc", solver_type=SOLVER, absolute_error=1e10,
                     relative_error=RELERR, maximum_iterations=30)
        except ds.error:
            h /= 2
            ds.set_parameter(device=DEV, name=GetContactBiasName("anode"), value=V)
            if h < 1e-3:
                log("  не сходится у %.3f В, останавливаюсь" % V); break
            continue
        V = Vn; I = anode_current(); out.append((V, I))
        log("  V=%.3f  I=%.5e А   (%.0f с)" % (V, I, time.time() - t0))
        h = min(step, h * 1.5)
    return out
