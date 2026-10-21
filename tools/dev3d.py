# -*- coding: utf-8 -*-
"""3D-диод в DEVSIM: загрузка сетки Gmsh, легирование, равновесие, развёртка."""

import devsim as ds
from devsim.python_packages.simple_physics import (
    SetSiliconParameters, CreateSiliconPotentialOnly, CreateSiliconPotentialOnlyContact,
    CreateSiliconDriftDiffusion, CreateSiliconDriftDiffusionAtContact, GetContactBiasName)
from devsim.python_packages.model_create import (
    CreateSolution, CreateNodeModel, CreateEdgeModel, CreateEdgeModelDerivatives)

from dd3d import CT_DOPING, CT_BETA, VSAT    # та же модель подвижности, что в своём решателе

NA, ND, LZ = 1.4e17, 1.0e17, 0.8e-4
DEV, REG = "diode", "si"
SOLVER = "direct"           # "iterative" (GMRES) экономит память, но под смещением врёт
RELERR = 1e-8               # допуск Ньютона под смещением
RELERR0 = (1e-8, 1e-6, 1e-5)  # при 0 В по очереди, если 1e-8 не возьмётся (с float128 берётся)
MOBILITY = "ct"             # "ct" — Коги-Томас + насыщение по полю вдоль ребра, как в dd3d;
                            # "element" — то же, но насыщение по полному |E| на тетраэдре;
                            # "const" — 400/200 из simple_physics
E_SMOOTH = 1.0              # В/см: |E| = sqrt(E² + E_SMOOTH²), чтобы у производной не было излома в нуле
CONTACTS = ("anode", "cathode")


def use_direct(name="umfpack"):
    """Прямой решатель DEVSIM: "umfpack" (вшитый UMFPACK 5.1) или "pardiso" (MKL).

    На маке MKL нет, и DEVSIM сам берёт UMFPACK. На Windows из conda-окружения он находит
    mkl_rt и берёт Pardiso — а тот на FUJION (FX-8320, MKL 2025.0) после первой итерации
    отдаёт нулевую поправку: RelError обрывается ровно в 0, и Ньютон «сходится» на мусоре.
    Поэтому по умолчанию UMFPACK везде. Возвращает имя решателя, который реально работает.
    """
    if name == "umfpack":
        from devsim.umfpack import umfshim  # noqa: F401 — при импорте ставит direct_solver=custom
        return "UMFPACK 5.1, BLAS " + ",".join(ds.get_parameter(name="info")["math_libraries"])
    if name == "cudss":
        import cudss_shim                   # разложение на видеокарте, FP64
        return cudss_shim.install()
    if "mkl_pardiso" not in ds.get_parameter(name="info").get("direct_solver", ()):
        raise RuntimeError("MKL Pardiso не загружен — нужен mkl в окружении")
    ds.set_parameter(name="direct_solver", value="mkl_pardiso")
    return "MKL Pardiso, " + ds.get_parameter(name="info").get("mkl_version", "")


def extended_precision(on=True):
    """Модели и сборка уравнений в float128.

    Ток Шарфеттера-Гуммеля — разность потоков, а концентрации в приборе гуляют от ~1e3
    (неосновные) до 1.4e17 см^-3. В double эта разность упирается в округление: Ньютон
    застревает на RelError ~1e-5 и под смещением, а ток при малых напряжениях выходит
    мусором (миллиамперы вместо 1e-16 А). С extended_model + extended_equation сходимость
    квадратичная до ~1e-11 на каждом шаге. extended_solver (сам линейный решатель) не нужен:
    отдельно он не помогает, проверено на сетке 8.6 тыс. узлов.
    """
    for p in ("extended_model", "extended_equation"):
        ds.set_parameter(name=p, value=on)


def load(msh):
    extended_precision()
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


def mobility():
    """Подвижность на рёбрах — как в dd3d.py, чтобы три расчёта были сравнимы.

    mu0 = mu_min + (mu_max - mu_min) / (1 + (N/N_ref)^alpha)   — Коги-Томас по легированию,
          N — полное легирование, среднее по концам ребра;
    mu  = mu0 / (1 + (mu0·|E|/vsat)^beta)^(1/beta)            — насыщение скорости,
          E — поле вдоль ребра, beta = 2 для электронов и 1 для дырок.

    Подвижность зависит от потенциала, поэтому заданы и её производные:
    Ньютон получает полный якобиан, а не запаздывающую подвижность, как у Гуммеля в dd3d.
    """
    CreateNodeModel(DEV, REG, "NTotal", "Donors+Acceptors")
    # EnsureEdgeFromNodeModelExists из devsim 2.11 ничего не создаёт (условие в нём всегда
    # истинно), поэтому NTotal@n0/@n1 делаем сами; Potential@n0/@n1 уже есть от simple_physics
    ds.edge_from_node_model(device=DEV, region=REG, node_model="NTotal")
    CreateEdgeModel(DEV, REG, "NTotalEdge", "0.5*(NTotal@n0+NTotal@n1)")
    epar = "pow(((Potential@n0-Potential@n1)*EdgeInverseLength)^2 + %g, 0.5)" % E_SMOOTH ** 2
    CreateEdgeModel(DEV, REG, "EParallel", epar)
    CreateEdgeModelDerivatives(DEV, REG, "EParallel", epar, "Potential")
    for c in ("n", "p"):
        mn, mx, nref, a = CT_DOPING[c]
        b = CT_BETA[c]
        CreateEdgeModel(DEV, REG, "mu0_%s" % c,
                        "%g + %g/(1 + pow(NTotalEdge/%g, %g))" % (mn, mx - mn, nref, a))
        mu = "mu0_{c}*pow(1 + pow(mu0_{c}*EParallel/{v:g}, {b:g}), {ib:g})".format(
            c=c, v=VSAT, b=b, ib=-1.0 / b)
        CreateEdgeModel(DEV, REG, "mu_%s_edge" % c, mu)
        CreateEdgeModelDerivatives(DEV, REG, "mu_%s_edge" % c, mu, "Potential")


EN = ("@en0", "@en1", "@en2", "@en3")       # узлы тетраэдра в элементных моделях


def _elem(name, expr, variables=()):
    ds.element_model(device=DEV, region=REG, name=name, equation=expr)
    for v in variables:
        for e in EN:
            ds.element_model(device=DEV, region=REG, name="%s:%s%s" % (name, v, e),
                             equation="diff(%s, %s%s)" % (expr, v, e))


def element_currents():
    """Ток на элементах с насыщением скорости по полному полю (режим MOBILITY="element").

    На ребре видна только проекция поля, а рёбра тетраэдров идут под углом к току —
    насыщение недооценивается. Здесь вектор поля собирается на каждом тетраэдре из его
    рёбер, подвижность — Коги-Томас по легированию концов ребра и насыщение по |E|,
    ток — тот же поток Шарфеттера-Гуммеля, но элементной моделью (3D-аналог mos_physics.py).
    Площади граней ячеек при этом берёт сам DEVSIM, то есть завышенные
    (см. tools/voronoi3d.py) — поправка к ним есть только в dev_ise.py.
    """
    ds.element_from_edge_model(edge_model="ElectricField", device=DEV, region=REG)
    ds.element_from_edge_model(edge_model="ElectricField", device=DEV, region=REG,
                               derivative="Potential")
    ds.element_model(device=DEV, region=REG, name="Emag",
                     equation="pow(ElectricField_x^2 + ElectricField_y^2 + ElectricField_z^2 + %g, 0.5)"
                     % E_SMOOTH ** 2)
    for e in EN:
        ds.element_model(device=DEV, region=REG, name="Emag:Potential" + e, equation=(
            "(ElectricField_x*ElectricField_x:Potential{0} + ElectricField_y*ElectricField_y:Potential{0}"
            " + ElectricField_z*ElectricField_z:Potential{0})/Emag").format(e))
    CreateNodeModel(DEV, REG, "NTotal", "Donors+Acceptors")
    ds.edge_from_node_model(device=DEV, region=REG, node_model="NTotal")
    CreateEdgeModel(DEV, REG, "NTotalEdge", "0.5*(NTotal@n0+NTotal@n1)")
    for c in ("n", "p"):
        mn, mx, nref, a = CT_DOPING[c]
        b = CT_BETA[c]
        CreateEdgeModel(DEV, REG, "mu0_%s" % c,
                        "%g + %g/(1 + pow(NTotalEdge/%g, %g))" % (mn, mx - mn, nref, a))
        _elem("mu_%s_elem" % c, "mu0_{c}*pow(1 + pow(mu0_{c}*Emag/{v:g}, {b:g}), {ib:g})".format(
            c=c, v=VSAT, b=b, ib=-1.0 / b), ("Potential",))
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


def drift_diffusion():
    CreateSolution(DEV, REG, "Electrons")
    CreateSolution(DEV, REG, "Holes")
    ds.set_node_values(device=DEV, region=REG, name="Electrons", init_from="IntrinsicElectrons")
    ds.set_node_values(device=DEV, region=REG, name="Holes", init_from="IntrinsicHoles")
    if MOBILITY == "ct":
        mobility()
        CreateSiliconDriftDiffusion(DEV, REG, mu_n="mu_n_edge", mu_p="mu_p_edge")
    else:
        CreateSiliconDriftDiffusion(DEV, REG)
    for c in CONTACTS:
        CreateSiliconDriftDiffusionAtContact(DEV, REG, c)
    if MOBILITY == "element":
        element_currents()
    for i, tol in enumerate(RELERR0):
        try:
            ds.solve(type="dc", solver_type=SOLVER, absolute_error=1e10,
                     relative_error=tol, maximum_iterations=40)
            return tol
        except ds.error:
            if i == len(RELERR0) - 1:
                raise


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


def save_fields(path, dev=None, reg=None, mode=None):
    """Поля в узлах и тетраэдры — для картинок (Lab3_diode_3D/make_figures.py).

    Кроме полей пишется ток, втекающий в каждый узел, ровно в той дискретизации, что
    решал DEVSIM: поток по ребру (или ребру элемента) * площадь грани контрольного
    объёма. Внутри прибора он нулевой, сумма по узлам анода — ток контакта.
    mode: "element" — потоки элементные (MOBILITY="element"), иначе рёберные
    ElectronCurrent/HoleCurrent (dev_ise.py: поправка ячеек CR уже внутри них).
    """
    import numpy as np
    dev, reg = dev or DEV, reg or REG
    mode = mode or ("element" if MOBILITY == "element" else "edge")
    get = lambda n: np.array(ds.get_node_model_values(device=dev, region=reg, name=n))
    tets = np.array(ds.get_element_node_list(device=dev, region=reg), dtype=np.int32)
    node_current = np.zeros(len(get("x")))
    ds.edge_from_node_model(device=dev, region=reg, node_model="node_index")
    if mode == "element":
        for nm, eq in (("ia_", "node_index@en0"), ("ib_", "node_index@en1")):
            ds.element_model(device=dev, region=reg, name=nm, equation=eq)
        ev = lambda n: np.array(ds.get_element_model_values(device=dev, region=reg, name=n))
        flux = (ev("ElectronCurrentElem") + ev("HoleCurrentElem")) * ev("ElementEdgeCouple")
        ia, ib = ev("ia_"), ev("ib_")
    else:
        ee = lambda n: np.array(ds.get_edge_model_values(device=dev, region=reg, name=n))
        flux = (ee("ElectronCurrent") + ee("HoleCurrent")) * ee("EdgeCouple")
        ia, ib = ee("node_index@n0"), ee("node_index@n1")
    np.add.at(node_current, ia.astype(np.int64), flux)
    np.add.at(node_current, ib.astype(np.int64), -flux)
    np.savez_compressed(path, x=get("x"), y=get("y"), z=get("z"), psi=get("Potential"),
                        n=get("Electrons"), p=get("Holes"), C=get("NetDoping"), tets=tets,
                        node_current=node_current, area=get("ContactSurfaceArea"))
