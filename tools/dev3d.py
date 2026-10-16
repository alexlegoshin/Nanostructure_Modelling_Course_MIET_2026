# -*- coding: utf-8 -*-
"""3D-диод в DEVSIM: загрузка сетки Gmsh, легирование, равновесие, развёртка."""

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
    CreateSiliconDriftDiffusion(DEV, REG)
    for c in CONTACTS:
        CreateSiliconDriftDiffusionAtContact(DEV, REG, c)
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
