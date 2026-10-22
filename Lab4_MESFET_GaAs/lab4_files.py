# -*- coding: utf-8 -*-
"""Входные файлы ISE работы 4: структура, сетка и легирование MESFET со стоп-слоем.

Структура и легирование — как в примере методических указаний (Test/Task_1):
слои сверху вниз, ось y — вглубь, мкм; x — 0…15 (исток 0…5, канал 5…10, сток 10…15).

    S8a, S8b  0      … 0.1      n+ под истоком и стоком канала, 1e18
    S7        0.1    … 0.3      GaAs 4e17, в нём выемка под затвор до глубины 0.3 − h
    S6        0.3    … 0.301    GaAs, 1e14
    S5        0.301  … 0.304    AlGaAs (x = 1), стоп-слой, 1.5e18
    S4        0.304  … 0.304+h4 GaAs, N4
    S3        … + 0.006         GaAs, 7e17
    S2        … 1.05            GaAs, 1e14
    S1        1.05   … 2.05     подложка GaAs, 1e14
    S10, S11  0 … 1.05          n+ области истока и стока, 1e18

h — расстояние от затвора до стоп-слоя (верх S6), h4 — толщина слоя S4.
"""


def _f(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


def layers(h4, h):
    y4 = 0.304 + h4
    y3 = y4 + 0.006
    return {"yg": 0.3 - h, "y4": y4, "y3": y3}


def bnd(h4, h):
    L = layers(h4, h); yg, y4, y3 = (_f(L[k]) for k in ("yg", "y4", "y3"))
    return f"""GaAs "S10"
{{
\trectangle [(0, 0.0) (5, 1.05)]
}}

GaAs "S11"
{{
\trectangle [(10, 0.0) (15, 1.05)]
}}

GaAs "S8a"
{{
\trectangle [(5, 0.0) (7, 0.1)]
}}

GaAs "S8b"
{{
\trectangle [(8, 0.0) (10, 0.1)]
}}

GaAs "S7"
{{
\tpolygon [(5, 0.1) (7, 0.1) (7, {yg}) (8, {yg}) (8, 0.1) (10, 0.1) (10, 0.3) (5, 0.3)]
}}

GaAs "S6"
{{
\trectangle [(5, 0.3) (10, 0.301)]
}}

AlGaAs "S5"
{{
\trectangle [(5, 0.301) (10, 0.304)]
}}

GaAs "S4"
{{
\trectangle [(5, 0.304) (10, {y4})]
}}

GaAs "S3"
{{
\trectangle [(5, {y4}) (10, {y3})]
}}

GaAs "S2"
{{
\trectangle [(5, {y3}) (10, 1.05)]
}}

GaAs "S1"
{{
\trectangle [(0, 1.05) (15, 2.05)]
}}

Contact "Source"
{{
\tline [(0,0) (5,0)]
}}

Contact "Gate"
{{
\tline [(7,{yg}) (8,{yg})]
}}

Contact "Drain"
{{
\tline [(10,0) (15,0)]
}}
"""


# легирование слоёв, 1/см3 (S4 — по варианту)
DOPING = {"P10": 1e18, "P11": 1e18, "P1": 1e14, "P2": 1e14, "P3": 7e17,
          "P5": 1.5e18, "P6": 1e14, "P7": 4e17, "P8": 1e18}


def cmd(h4, h, N4):
    L = layers(h4, h); y4, y3 = _f(L["y4"]), _f(L["y3"])
    dop = dict(DOPING, P4=N4)
    consts = "\n".join(f"""    Constant "{k}"
    {{
      Species = "PhosphorusActiveConcentration"
      Value = {v:.2e}
    }}""" for k, v in dop.items())
    win = {"P_S10": ("P10", "0 0", "5 1.05"), "P_S11": ("P11", "10 0", "15 1.05"),
           "P_S8": ("P8", "5 0", "10 0.1"), "P_S7": ("P7", "5 0.1", "10 0.3"),
           "P_S6": ("P6", "5 0.3", "10 0.301"), "P_S5": ("P5", "5 0.301", "10 0.304"),
           "P_S4": ("P4", "5 0.304", "10 " + y4), "P_S3": ("P3", "5 " + y4, "10 " + y3),
           "P_S2": ("P2", "5 " + y3, "10 1.05"), "P_S1": ("P1", "0 1.05", "15 2.05")}
    places = "\n".join(f"""    Constant "{n}"
    {{
      Reference = "{r}"
      EvaluateWindow
      {{
        Element = rectangle [( {a} ) , ( {b} )]
        DecayLength = 0
      }}
      Replace
    }}""" for n, (r, a, b) in win.items())
    return f"""Title "Transistor"

Definitions {{
    Refinement "Mesh"
    {{
      MaxElementSize = (1.0, 0.5)
      MinElementSize = (0.1, 0.01)
      RefineFunction = MaxTransDiff(Variable="DopingConcentration",Value=1)
    }}
    Refinement "Mesh_1"
    {{
      MaxElementSize = (0.5, 0.05)
      MinElementSize = (0.01, 0.001)
      RefineFunction = MaxTransDiff(Variable="DopingConcentration",Value=1)
    }}
    Refinement "M3" {{ MaxElementSize = (0.4 0.0006) MinElementSize = (0.02 0.0006) }}
    Refinement "M4" {{ MaxElementSize = (0.4 0.004)  MinElementSize = (0.02 0.004) }}
    Refinement "M5" {{ MaxElementSize = (0.4 0.001)  MinElementSize = (0.02 0.0005) }}
    Refinement "M6" {{ MaxElementSize = (0.4 0.0003) MinElementSize = (0.02 0.0001) }}
    Refinement "M7" {{ MaxElementSize = (0.4 0.02)   MinElementSize = (0.02 0.01) }}

{consts}
}}

Placements {{
    Refinement "Default Region" {{ Reference = "Mesh" }}
    Refinement "M_Mesh_1" {{ Reference = "Mesh_1" RefineWindow = rectangle [(3, 0.0) (12, 0.75)] }}
    Refinement "M_S7" {{ Reference = "M7" RefineWindow = rectangle [( 5 0.1 ) , ( 10 0.3 )] }}
    Refinement "M_S6" {{ Reference = "M6" RefineWindow = rectangle [( 5 0.3 ) , ( 10 0.301 )] }}
    Refinement "M_S5" {{ Reference = "M5" RefineWindow = rectangle [( 5 0.301 ) , ( 10 0.304 )] }}
    Refinement "M_S4" {{ Reference = "M4" RefineWindow = rectangle [( 5 0.304 ) , ( 10 {y4} )] }}
    Refinement "M_S3" {{ Reference = "M3" RefineWindow = rectangle [( 5 {y4} ) , ( 10 {y3} )] }}

{places}
}}
"""


_DES_HEAD = """File {
\tGrid = "t_msh.grd"
\tDoping = "t_msh.dat"
\tPlot = "t_des.dat"
\tCurrent = "t_msh.plt"
\tOutput = "t_des.log"
}

Electrode {
\t{ Name="Source" Voltage=0.0 }
\t{ Name="Drain" Voltage=0.0 }
\t{ Name="Gate" Schottky barrier=0.75 Voltage=0 }
}

Physics {
\tAreaFactor = 1000
\tMobility ( DopingDependence HighFieldSaturation Enormal )
\tEffectiveIntrinsicDensity ( OldSlotboom )
\tRecombination ( SRH ( DopingDependence ) )
}

Physics ( Material = "AlGaAs" ) {
\tMoleFraction( RegionName="S5" XFraction=1.0 Grading=0.03 )
}

Plot {
\teDensity hDensity eCurrent hCurrent
\tPotential SpaceCharge ElectricField
\teMobility hMobility eVelocity hVelocity
\tDoping DonorConcentration AcceptorConcentration
\tCurrent/Vector
}

Math {
\tExtrapolate
\tDerivatives
\tRelErrControl
\tNewDiscretization
}
"""

_STEP = """\tQuasistationary (
\t\tMaxStep={step}
\t\t{goals}
\t) {{
\t\tCoupled {{ Poisson Electron Hole }}
\t}}
"""


def _tag(vg):
    return ("p" if vg > 0 else "m" if vg < 0 else "") + "%02d" % round(abs(vg) * 10)


def des_output(vgs, vd=4.0):
    """Задания 1 и 4: при каждом Vg из vgs — Id(Vd) от 0 до vd. Состояния при Vg
    сохраняются по очереди (Save), затем из каждого — развёртка по стоку (Load)."""
    tags = [_tag(v) if any(x < 0 for x in vgs) else "%02d" % round(v * 10) for v in vgs]
    s = "\nSolve {\n\tCoupled ( Iterations=100 ) { Poisson }\n\tCoupled { Poisson Electron Hole }\n"
    s += '\tSave (FilePrefix="Vg_%s_")\n' % ("00")
    for v, t in zip(vgs, tags):
        if abs(v) < 1e-12:
            continue
        s += _STEP.format(step=0.1, goals='Goal {Name="Gate" Voltage=%g}' % v)
        s += '\tSave (FilePrefix="Vg_%s_")\n' % t
    for t in ["00"] + [t for v, t in zip(vgs, tags) if abs(v) > 1e-12]:
        s += '\tLoad (FilePrefix="Vg_%s_")\n\tNewCurrent="Vg_%s_"\n' % (t, t)
        s += _STEP.format(step=0.02, goals='Goal {Name="Drain" Voltage=%g}' % vd)
    return _DES_HEAD + s + "}\n"


def des_transfer(vg0, step, vd=2.0, vg1=1.5):
    """Задания 2 и 3: выход на Vd и начальный Vg, затем Id(Vg) от vg0 до vg1 (New_t_msh.plt)."""
    s = "\nSolve {\n\tCoupled ( Iterations=100 ) { Poisson }\n\tCoupled { Poisson Electron Hole }\n"
    s += _STEP.format(step=0.1, goals='Goal {Name="Drain" Voltage=%g}\n\t\tGoal {Name="Gate" Voltage=%g}' % (vd, vg0))
    s += '\tNewCurrent="New_"\n'
    s += _STEP.format(step=step, goals='Goal {Name="Gate" Voltage=%g}' % vg1)
    return _DES_HEAD + s + "}\n"


def des_transfer_jumps(vg0, segments, vd=2.0):
    """Как des_transfer, но развёртка по затвору — участками [(Vg до, шаг, прыжок)].
    У ISE 7.0 на некоторых структурах есть узкие напряжения, где метод Ньютона не сходится
    ни при каком шаге (при h = 0.01 — около Vg = −0.15 В); их проходит один крупный шаг
    (прыжок = True: шаг на весь участок, без дробления). Неудачный участок ISE пропускает
    и продолжает со следующего, поэтому «лесенка» из прыжков проходит любые такие стены."""
    s = "\nSolve {\n\tCoupled ( Iterations=100 ) { Poisson }\n\tCoupled { Poisson Electron Hole }\n"
    s += _STEP.format(step=0.1, goals='Goal {Name="Drain" Voltage=%g}\n\t\tGoal {Name="Gate" Voltage=%g}' % (vd, vg0))
    s += '\tNewCurrent="New_"\n'
    for vg, step, jump in segments:
        st = "InitialStep=1 MaxStep=1 MinStep=0.99" if jump else "MaxStep=%g MinStep=1e-6" % step
        s += _STEP.replace("MaxStep={step}", st).format(goals='Goal {Name="Gate" Voltage=%g}' % vg)
    return _DES_HEAD + s + "}\n"
