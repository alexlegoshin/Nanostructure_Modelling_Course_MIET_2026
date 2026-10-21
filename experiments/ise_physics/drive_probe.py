# -*- coding: utf-8 -*-
"""Какую движущую силу подставляет в насыщение ISE: обращение формулы Канали по узлам.

F_eff = vsat/mu0 · ((mu0/mu)^beta − 1)^(1/beta) — по подвижности ISE в узле (sX_des.dat, 4 В).
Сравнивается с кандидатами: |E|, |E·J|/|J| (поле вдоль полного тока), |E_z|.

    python drive_probe.py [A|B]
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import dfise
from dev_ise import CANALI
from mobility_probe import masetti

ISE = os.path.join(HERE, "..", "..", "Lab3_diode_3D", "ise")


def stats(name, Feff, cand, sel):
    r = Feff[sel] / np.maximum(cand[sel], 1e-30)
    lr = np.log10(r)
    print("    %-16s F_eff/кандидат: медиана %.3f, 10–90%% %.3f … %.3f, разброс lg %.3f"
          % (name, np.median(r), *np.percentile(r, [10, 90]), lr.std()))


def main():
    t = sys.argv[1] if len(sys.argv) > 1 else "A"
    d = dfise.read_dataset(os.path.join(ISE, "s%s_des.dat" % t))
    N = d["DonorConcentration"] + d["AcceptorConcentration"]
    Ev = d["ElectricField-Vector"]; E = np.linalg.norm(Ev, axis=1)
    J = d["TotalCurrentDensity-Vector"]; Jn = np.linalg.norm(J, axis=1)
    Epar = np.abs((Ev * J).sum(1)) / np.maximum(Jn, 1e-30)
    print("|E| из вектора против ElectricField: медиана отношения %.4f"
          % np.median(E / np.maximum(d["ElectricField"], 1e-30)))
    for k, mu_name in (("n", "eMobility"), ("p", "hMobility")):
        vs, b = CANALI[k]
        mu0 = masetti(N, k); mu = d[mu_name]
        x = np.clip(mu0 / mu, 1.0, None) ** b - 1.0
        Feff = vs / mu0 * x ** (1.0 / b)
        sel = (Feff > 3e3) & (E > 3e3)              # где насыщение заметно
        print("\n== %s: узлов с заметным насыщением %d" % (k, sel.sum()))
        stats("|E|", Feff, E, sel)
        stats("|E·J|/|J|", Feff, Epar, sel)
        stats("|E_z|", Feff, np.abs(Ev[:, 2]), sel)
        stats("|E_x,y|", Feff, np.linalg.norm(Ev[:, :2], axis=1), sel)


if __name__ == "__main__":
    main()
