#!/usr/bin/env python3
"""Сгенерировать проекты ISE TCAD для всех 25 вариантов лаб 1-2.

Базовая структура из методички рассчитана на диод толщиной d = 2 мкм.
В варианте толщина другая, поэтому всё вдоль Oy делится на k = 2/d,
а вдоль Ox остаётся как есть — так требуют «Общие замечания» в методичке.

На каждый вариант три проекта:
    T1 — задание 1, крупная сетка,  Voltage = 4
    T2 — задание 2, ячейки вдвое мельче, Voltage = 4
    T4 — задание 4, сетка как в T2,  Voltage = 0
Задание 3 отдельных файлов не требует: это сравнение T1 и T2 в inspect.
"""
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "variants")

# (номер, d мкм, NB, NAs) — таблица вариантов 1 из методички
TABLE = []
_d = [1, 0.8, 0.6, 0.4]
_nb = ["1.2e+17", "1.4e+17", "1.6e+17", "1.8e+17", "1.0e+18"]
_nas = ["1.0e+17", "1.2e+17", "1.4e+17", "1.6e+17", "1.8e+17"]
for i in range(25):
    TABLE.append((i + 1, _d[i % 4], _nb[i % 5], _nas[i // 5]))


def f(x):
    """Короткая запись числа: 0.25, -1.5, 0 — без хвостов вроде 0.30000000000000004."""
    s = "%.6f" % x
    s = s.rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def bnd(h):
    return f"""Silicon "SiW"
{{
	rectangle [(-1.5,{f(-h)}) (1.5,{f(h)})]
}}

Contact "Anode"
{{
	line[(-0.5,{f(-h)}) (0.5,{f(-h)})]
}}

Contact "Cathode"
{{
	line[(-1.5,{f(h)}) (1.5,{f(h)})]
}}
"""


def cmd(h, k, nb, nas, fine):
    """fine=False — сетка задания 1, fine=True — вдвое мельче (задание 2)."""
    s = 0.5 if fine else 1.0
    m1max_x, m1max_y = 0.5 * s, 0.5 * s / k
    m1min_x, m1min_y = 0.1 * s, 0.1 * s / k
    m2max_x, m2max_y = 0.2 * s, 0.2 * s / k
    m2min_x, m2min_y = 0.01 * s, 0.01 * s / k
    return f"""Title "Sharp Diode"

Definitions {{

  # Refinement regions
    Refinement "Mesh1"
    {{
      MaxElementSize = ({f(m1max_x)} {f(m1max_y)})
      MinElementSize = ({f(m1min_x)} {f(m1min_y)})
      RefineFunction = MaxTransDiff(Variable = "DopingConcentration", Value = 1)
    }}

    Refinement "Mesh2"
    {{
      MaxElementSize = ({f(m2max_x)} {f(m2max_y)})
      MinElementSize = ({f(m2min_x)} {f(m2min_y)})
    }}

  # Profiles
    Constant "BW"
    {{
      Species = "BoronActiveConcentration"
      Value = {nb}
    }}
    Constant "AsW"
    {{
      Species = "ArsenicActiveConcentration"
      Value = {nas}
    }}
}}

Placements {{

  # Refinement regions
    Refinement "Mesh1"
    {{
      Reference = "Mesh1"
      RefineWindow = rectangle [( -1.5 {f(-h)} ) , ( 1.5 {f(h)} )]
    }}
    Refinement "Mesh2"
    {{
      Reference = "Mesh2"
      RefineWindow = rectangle [( -1.0 {f(-h)} ) , ( 1.0 {f(-h / 2)} )]
    }}

  # Profiles
    Constant "BW"
    {{
      Reference = "BW"
      EvaluateWindow
      {{
        Element = rectangle [( -1.5 {f(-h)} ) , ( 1.5 0 )]
        DecayLength = 0
      }}
    }}

    Constant "AsW"
    {{
      Reference = "AsW"
      EvaluateWindow
      {{
        Element = rectangle [( -1.5 0 ) , ( 1.5 {f(h)} )]
        DecayLength = 0
      }}
    }}

}}
"""


def des(voltage):
    return f"""File {{
* input files:
	Grid = "sh1_msh.grd"
	Doping = "sh1_msh.dat"

* output files:
	Plot = "sh1_des.dat"
	Current = "sh1_des.plt"
	Output = "sh1_des.log"
}}

Electrode {{
	{{ Name="Anode"   Voltage=0.0 }}
	{{ Name="Cathode" Voltage=0.0 }}
}}

Physics {{
	Mobility( DopingDep HighFieldsat Enormal )
	EffectiveIntrinsicDensity(BandGapNarrowing (OldSlotboom))
}}

Plot {{
	eDensity hDensity eCurrent hCurrent
	Potential SpaceCharge ElectricField
	eMobility hMobility eVelocity hVelocity
	Doping DonorConcentration AcceptorConcentration
	Current/Vector
}}

Math {{
	Extrapolate
	Derivatives
	RelErrControl
	NewDiscretization
}}

Solve {{
	Poisson
	Coupled {{ Poisson Electron Hole}}

	Quasistationary (
		MaxStep=0.01
		Goal {{ Name="Anode" Voltage={voltage} }}
	)
	{{ Coupled {{ Poisson Electron Hole}} }}
}}
"""


def main():
    for num, d, nb, nas in TABLE:
        h, k = d / 2.0, 2.0 / d
        for task, fine, volt in (("T1", False, 4), ("T2", True, 4), ("T4", True, 0)):
            p = os.path.join(OUT, "V%02d" % num, task)
            os.makedirs(p, exist_ok=True)
            open(os.path.join(p, "sh1.bnd"), "w").write(bnd(h))
            open(os.path.join(p, "sh1.cmd"), "w").write(cmd(h, k, nb, nas, fine))
            open(os.path.join(p, "sh1_des.cmd"), "w").write(des(volt))
            # сечение из спецификации отчёта: (0, -d/2) — (0, d/2)
            open(os.path.join(p, "cut.txt"), "w").write(
                "0.0\n%s\n0.0\n%s\n" % (f(-h), f(h))
            )
    print("вариантов: %d, проектов: %d" % (len(TABLE), len(TABLE) * 3))
    for num, d, nb, nas in TABLE[:5]:
        print("  V%02d  d=%-4s NB=%-8s NAs=%s" % (num, d, nb, nas))
    print("  ...")


if __name__ == "__main__":
    main()
