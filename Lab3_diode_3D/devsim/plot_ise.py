# -*- coding: utf-8 -*-
"""ВАХ диодов A и B: DEVSIM с физикой ISE против ISE и эталона преподавателя.

    python plot_ise.py [суффикс]     # iv_ise_A_isemesh_clip<суффикс>.json, iv_ise_B_isemeshA_clip<суффикс>.json

Пишет ../results/devsim_ise/вах.png и печатает таблицу для README.
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import viz

OUT = os.path.join(HERE, "..", "results", "devsim_ise")


def load(name):
    V, I = np.array(json.load(open(os.path.join(HERE, name)))).T
    return V, np.abs(I)


def main():
    sfx = sys.argv[1] if len(sys.argv) > 1 else ""
    A = load("iv_ise_A_isemesh_clip%s.json" % sfx)
    B = load("iv_ise_B_isemeshA_clip%s.json" % sfx)
    d = viz.read_plt(os.path.join(HERE, "..", "ise", "sA_des.plt"))
    ise = np.asarray(d["Anode OuterVoltage"]), np.abs(np.asarray(d["Anode TotalCurrent"]))
    ref = json.load(open(os.path.join(HERE, "reference_iv.json")))
    rA, rB = (np.array(ref[k]) for k in ("A", "B"))

    os.makedirs(OUT, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.4, 4.8), dpi=150)
    ax.plot(rA[0], rA[1] * 1e3, color="#d62728", lw=6, alpha=0.25, label="эталон преподавателя, A")
    ax.plot(rB[0], rB[1] * 1e3, color="#222222", lw=6, alpha=0.25, label="эталон преподавателя, B")
    ax.plot(ise[0], ise[1] * 1e3, "o", color="#d62728", ms=4, mfc="none", label="ISE, наш прогон, A")
    ax.plot(A[0], A[1] * 1e3, color="#d62728", lw=1.6, label="DEVSIM, физика ISE, A")
    ax.plot(B[0], B[1] * 1e3, color="#222222", lw=1.6, label="DEVSIM, физика ISE, B")
    ax.set_xlim(0, 4); ax.set_ylim(0, None)
    ax.set_xlabel("U, В"); ax.set_ylabel("I, мА")
    ax.grid(ls=":", color="#999999")
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax.set_title("Лаба 3: ВАХ диодов A и B (сетка ISE, вариант 2)", fontsize=10)
    fig.tight_layout()
    png = os.path.join(OUT, "вах.png")
    fig.savefig(png); print("картинка:", os.path.abspath(png))

    def at(V, I, v):
        return float(np.interp(v, V, I))

    print("\n| U, В | A, мА | B, мА | B ниже A | ISE A, мА | эталон A | эталон B | эталон: B ниже A |")
    print("|---|---|---|---|---|---|---|---|")
    for v in (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 3.95):
        a, b, i = at(*A, v), at(*B, v), at(*ise, v)
        ra, rb = at(*rA, v), at(*rB, v)
        print("| %.2f | %.3f | %.3f | %.0f %% | %.3f | %.3f | %.3f | %.0f %% |"
              % (v, a * 1e3, b * 1e3, 100 * (1 - b / a), i * 1e3, ra * 1e3, rb * 1e3, 100 * (1 - rb / ra)))


if __name__ == "__main__":
    main()
