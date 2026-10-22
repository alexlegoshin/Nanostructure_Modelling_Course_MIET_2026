# -*- coding: utf-8 -*-
"""Входные файлы ISE работы 5: MESFET в цепи амплитудного модулятора (mixed mode).

Структура и сетка — как в примере методических указаний (Test_1): GaAs 4 × 0.36 мкм
с двумя ступенями выемки под затвор, затвор Шоттки 1.75…2.25 мкм на глубине 0.08.
Легирование (фосфор вместо кремния): 1e14 однородно + гауссов канал
N01·exp(−(y − 0.1157)²/a01²) + гауссовы омические области 3e18 у поверхности.
От варианта зависят N01 и a01 (канал), частота несущей f1 и амплитуда модулирующего
сигнала um2.
"""
import math

BND = """GaAs "S"
{
\tpolygon [(0,0) (0.8,0) (0.8,0.04) (1.6,0.04) (1.6,0.08) (2.4,0.08) (2.4,0.04) (3.2,0.04)
(3.2,0) (3.6,0) (4,0) (4,0.36) (0,0.36)]
}

Contact "source"
{
\tline [(0,0) (0.4,0)]
}

Contact "gate"
{
\tline [(1.75,0.08) (2.25,0.08)]
}

Contact "drain"
{
\tline [(3.6,0) (4,0)]
}
"""


def cmd(N01, a01):
    return f"""Title "Transistor"

Definitions {{
    Refinement "Default Region"
    {{
      MaxElementSize = (0.2 0.02 )
      MinElementSize = (0.02 0.002 )
      RefineFunction = MaxTransDiff(Variable = "DopingConcentration", Value = 1)
    }}
    Refinement "Mesh1"
    {{
      MaxElementSize = (0.1 0.01 )
      MinElementSize = (0.01 0.001 )
      RefineFunction = MaxTransDiff(Variable = "DopingConcentration", Value = 1)
    }}
    AnalyticalProfile "P1"
    {{
      Species = "PhosphorusActiveConcentration"
      Function = Gauss(PeakPos = 0, PeakVal = {N01:.1e}, StdDev = {a01:g})
      LateralFunction = Gauss(Factor = 0)
    }}
    AnalyticalProfile "P2"
    {{
      Species = "PhosphorusActiveConcentration"
      Function = Gauss(PeakPos = 0, PeakVal = 3e+018, StdDev = 0.02)
      LateralFunction = Gauss(Factor = 0)
    }}
    Constant "P3"
    {{
      Species = "PhosphorusActiveConcentration"
      Value = 1e+014
    }}
}}

Placements {{
    Refinement "Default Region" {{ Reference = "Default Region" }}
    Refinement "Mesh1" {{ Reference = "Mesh1" RefineWindow = rectangle [( 1.25 0.04 ) , ( 2.75 0.2 )] }}
    AnalyticalProfile "P1" {{ Reference = "P1" ReferenceElement {{ Element = line [( 0 0.1157 ) , ( 4 0.1157 )] }} }}
    AnalyticalProfile "P2" {{ Reference = "P2" ReferenceElement {{ Element = line [( 0 0 ) , ( 4 0 )] }} }}
    Constant "P3" {{ Reference = "P3" EvaluateWindow {{ Element = rectangle [( 0 0 ) , ( 4 0.36 )] DecayLength = 0 }} }}
}}
""".replace("e+17", "e+017")


# неполная ионизация: параметры dessis по умолчанию, кроме фосфора — у него энергия
# кремния в GaAs (6 мэВ) вместо фосфора в кремнии (45 мэВ)
_ION = (("As", 0.054, 2), ("P", 0.006, 2), ("Sb", 0.039, 2), ("B", 0.045, 4), ("In", 0.16, 4),
        ("N", 0.045, 2), ("NDopant", 0.045, 2), ("PDopant", 0.045, 4))
ION_PAR = ('Material = "GaAs" {\n\nIonization\n{\n' + "\n".join(
    "\tE_%s_0 = %g\t# [eV]\n\talpha_%s = 3.1000e-08\t# [eV cm]\n\tg_%s = %d\t# [1]\n"
    "\tXsec_%s = 1.0000e-12\t# [cm^2/sec]\n" % (n, e, n, n, g, n) for n, e, g in _ION) +
    "\tNdCrit = 1.0000e+22\t# [cm-3]\n\tNaCrit = 1.0000e+22\t# [cm-3]\n}\n\n}\n")


DEVICE = """\tFile {
\t\tGrid = "t_msh.grd"
\t\tDoping = "t_msh.dat"
\t\tParam = "Ion.par"
\t\t%s
\t}
\tElectrode {
\t\t{ Name="source" Voltage=0.0 }
\t\t{ Name="drain" Voltage=0.0 }
\t\t{ Name="gate" Schottky barrier=0.75 Voltage=0 }
\t}
\tPhysics {
\t\tAreaFactor = 1000
\t\tIncompleteIonization
\t\tMobility ( DopingDependence HighFieldSaturation )
\t}
"""

PLOT = """Plot {
\teDensity hDensity eCurrent hCurrent
\tPotential SpaceCharge ElectricField
\teMobility hMobility eVelocity hVelocity
\tDoping DonorConcentration AcceptorConcentration
\tCurrent/Vector
}
"""

MATH = """Math {
\tExtrapolate
\tDerivatives
\tRelErrControl
\tNewDiscretization
}
"""


def _qs(goals, step="MaxStep=0.1", extra=""):
    g = "\n".join("\t\tGoal {Name=\"%s\" Voltage=%g}" % kv for kv in goals)
    return "\tQuasistationary (\n\t\t%s%s\n%s\n\t) {\n\t\tCoupled { Poisson Electron Hole }\n\t}\n" % (step, extra, g)


def _single(solve):
    head = DEVICE.replace("\t\t%s", '\t\tPlot = "t_des.dat"\n\t\tCurrent = "t_des.plt"\n\t\tOutput = "t_des.log"')
    head = "\n".join(l[1:] if l.startswith("\t") else l for l in head.splitlines())
    return head + "\n" + PLOT + MATH + "\nSolve {\n\tCoupled ( Iterations=100 ) { Poisson }\n\tCoupled { Poisson Electron Hole }\n" + solve + "}\n"


def _tag(v):
    return ("p" if v >= 0 else "m") + "%02d" % round(abs(v) * 10)


def des_family(vgs=(0.8, 0.0, -0.8, -1.6, -2.4), vd=2.0):
    """Семейство Id(Vd) при нескольких Vg (Vg_<tag>_t_des.plt)."""
    s = ""
    for v in vgs:
        s += _qs([("gate", v)]) + '\tSave (FilePrefix="Vg_%s")\n' % _tag(v)
    for v in vgs:
        s += '\tLoad (FilePrefix="Vg_%s")\n\tNewCurrent="Vg_%s_"\n' % (_tag(v), _tag(v))
        s += _qs([("drain", vd)], "MaxStep=0.02")
    return _single(s)


def des_gate(vd=1.0, vg0=-10.0, vg1=2.0):
    """Id(Vg) при Vd = 1 В (New_t_des.plt) — для порога."""
    s = _qs([("drain", vd), ("gate", vg0)])
    s += '\tNewCurrent="New_"\n' + _qs([("gate", vg1)], "InitialStep=1e-3 MaxStep=0.01 MinStep=1e-15")
    return _single(s)


def des_family2(vds=(0.1, 0.2, 0.5, 0.8, 1.0, 1.5, 2.0), vg0=-10.0, vg1=2.0):
    """Семейство Id(Vg) при нескольких Vd (Vd_<мВ/10>_t_des.plt)."""
    s = '\tSave (FilePrefix="VdVg_00")\n'
    tag = lambda v: "%03d" % round(v * 100)
    for v in vds:
        s += '\tLoad (FilePrefix="VdVg_00")\n' + _qs([("drain", v), ("gate", vg0)], "InitialStep=1e-3 MaxStep=0.1 MinStep=1e-15")
        s += '\tSave (FilePrefix="Vd_%s")\n' % tag(v)
    for v in vds:
        s += '\tLoad (FilePrefix="Vd_%s")\n\tNewCurrent="Vd_%s_"\n' % (tag(v), tag(v))
        s += _qs([("gate", vg1)], "InitialStep=1e-3 MaxStep=0.01 MinStep=1e-15", "\n\t\tIncrement = 1.1")
    return _single(s)


def inductance(f0, C=1.25e-6):
    """L контура с резонансом на f0 при заданной ёмкости: f0 = 1/(2π√(LC))."""
    return 1.0 / ((2 * math.pi * f0) ** 2 * C)


def des_circuit(vt, f1, um2, um1=0.4, f2=1e3, vd=1.0, rlc=None, final=4e-3, maxstep=2e-5):
    """Задание 3 (rlc=None): сумма vt + um1·sin(2πf1 t) + um2·sin(2πf2 t) на затворе, Vd = 1 В.
    Задание 4: в цепи стока параллельный контур (R, C, L) между n4 (сток) и n6 (питание)."""
    sys_ = ["\tVsource_pset v1 (n1 n0) { dc = %g }" % vt,
            "\tVsource_pset v2 (n2 n1) { sine = ( 0.0 %g %g 0.0 0.0) }" % (um1, f1),
            "\tVsource_pset v3 (n3 n2) { sine = ( 0.0 %g %g 0.0 0.0) }" % (um2, f2)]
    if rlc is None:
        sys_ += ["\tVsource_pset v4 (n4 n0) { dc = %g }" % vd, "\tResistor_pset r (n5 n0) { resistance = 1 }"]
        nodes, sets = "n0 n1 n2 n3 n4 n5", ["\tSet (n0 = 0)", "\tSet (n4 = %g)" % vd, "\tSet (n5 = 0.0)"]
    else:
        R, C, L = rlc
        sys_ += ["\tVsource_pset v4 (n6 n0) { dc = %g }" % vd, "\tResistor_pset r (n5 n0) { resistance = 1 }",
                 "\tResistor_pset r1 (n4 n6) { resistance = %g }" % R,
                 "\tCapacitor_pset c (n4 n6) { capacitance = %g }" % C,
                 "\tInductor_pset l (n4 n6) { inductance = %.4g }" % L]
        nodes, sets = "n0 n1 n2 n3 n4 n5 n6", ["\tSet (n0 = 0)", "\tSet (n5 = 0.0)"]
    sys_ += ['\tMESFET fet ( "source"=n5 "gate"=n3 "drain"=n4 )'] + sets + ['\tPlot "nodes.plt" (time() %s)' % nodes]
    dev = DEVICE % 'Plot = "des.dat"\n\t\tCurrent = "des.plt"'
    return ("Device MESFET {\n" + dev + "}\n\nSystem {\n" + "\n".join(sys_) + "\n}\n\n" + PLOT +
            "Math {\n\tIterations = 13\n\tExtrapolate\n\tDerivatives\n\tRelErrControl\n\tNewDiscretization\n"
            "\tNoCheckTransientError\n}\n\nSolve {\n\tCoupled { Poisson }\n"
            "\tCoupled { Poisson Electron Hole Contact Circuit }\n\tUnset (n4)\n\tUnset (n5)\n"
            '\tNewCurrent="New_"\n\tTransient (\n\t\tInitialTime=0 FinalTime=%g\n'
            "\t\tInitialStep=1e-7 MaxStep=%g MinStep=1e-36\n\t\tIncrement=1.1\n\t) {\n"
            "\t\tCoupled { Poisson Electron Hole Contact Circuit }\n\t}\n}\n" % (final, maxstep))
