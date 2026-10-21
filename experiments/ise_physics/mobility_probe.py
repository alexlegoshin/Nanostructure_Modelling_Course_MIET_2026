# -*- coding: utf-8 -*-
"""Что на самом деле считает ISE: подвижности и скорости в узлах из sA_des.dat (4 В).

ISE пишет в .dat eMobility, hMobility, eVelocity, hVelocity, ElectricField и легирование.
Отсюда:
  F = v / mu            — движущая сила, которую ISE подставил в насыщение;
  mu_low(N)             — сравнение с Масетти (параметры tools/dev_ise.py);
  mu / mu_low против F  — подгонка Канали: vsat, beta.

    python mobility_probe.py [A|B]
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import dfise
from dev_ise import MASETTI, CANALI

ISE = os.path.join(HERE, "..", "..", "Lab3_diode_3D", "ise")


def masetti(N, kind):
    m1, m2, mu1, pc, cr, cs, a, b, mc = MASETTI[kind]
    return m1 * np.exp(-pc / N) + (mc - m2) / (1 + (N / cr) ** a) - mu1 / (1 + (cs / N) ** b)


def canali(mu0, F, vsat, beta):
    return mu0 / (1 + (mu0 * F / vsat) ** beta) ** (1 / beta)


def main():
    t = sys.argv[1] if len(sys.argv) > 1 else "A"
    d = dfise.read_dataset(os.path.join(ISE, "s%s_des.dat" % t))
    Nd, Na = d["DonorConcentration"], d["AcceptorConcentration"]
    N = Nd + Na
    E = d["ElectricField"]
    print("узлов %d; |E|: медиана %.3g, макс %.3g В/см" % (len(N), np.median(E), E.max()))
    for k, mu_name, v_name in (("n", "eMobility", "eVelocity"), ("p", "hMobility", "hVelocity")):
        mu, v = d[mu_name], d[v_name]
        mu0 = masetti(N, k)
        # eVelocity у ISE — не mu·F (в узлах у анода ~0 при |E| 2.6e5), а подвижность там
        # ровно Канали от |E|: движущая сила — модуль поля в узле
        F = E.copy() if "--velocity" not in sys.argv else v / mu
        ok = np.isfinite(F) & (mu > 0)
        print("\n== %s: подвижность ISE от %.1f до %.1f" % (k, mu.min(), mu.max()))
        # 1) низкополевая часть: узлы с маленькой движущей силой
        low = ok & (F < 1e3)
        if low.any():
            r = mu[low] / mu0[low]
            print("  F < 1e3 В/см: %d узлов, mu_ISE / Масетти = %.4f … %.4f (медиана %.4f)"
                  % (low.sum(), r.min(), r.max(), np.median(r)))
        # 2) движущая сила против |E|
        rf = F[ok] / np.maximum(E[ok], 1e-30)
        print("  F = v/mu против |E|: отношение медиана %.4f, 10-90%% %.4f … %.4f"
              % (np.median(rf), *np.percentile(rf, [10, 90])))
        # 3) подгонка Канали по всем узлам: перебор vsat, beta
        vs0, b0 = CANALI[k]
        best = None
        for vs in vs0 * np.linspace(0.6, 1.4, 81):
            for b in np.linspace(0.6, 2.4, 91):
                pred = canali(mu0[ok], F[ok], vs, b)
                e = np.sqrt(np.mean(np.log(pred / mu[ok]) ** 2))
                if best is None or e < best[0]:
                    best = (e, vs, b)
        pred0 = canali(mu0[ok], F[ok], vs0, b0)
        e0 = np.sqrt(np.mean(np.log(pred0 / mu[ok]) ** 2))
        print("  Канали с параметрами dev_ise (vsat %.3g, beta %.3f): ошибка lg %.4f" % (vs0, b0, e0 / np.log(10)))
        print("  лучшая подгонка: vsat %.4g, beta %.3f: ошибка lg %.4f" % (best[1], best[2], best[0] / np.log(10)))
        worst = np.argsort(-np.abs(np.log(pred0 / mu[ok])))[:5]
        idx = np.where(ok)[0][worst]
        for i in idx:
            print("    узел %4d: N=%.2e F=%.2e |E|=%.2e mu_ISE=%.1f Масетти=%.1f Канали=%.1f"
                  % (i, N[i], F[i], E[i], mu[i], mu0[i], canali(mu0[i], F[i], vs0, b0)))


if __name__ == "__main__":
    main()
