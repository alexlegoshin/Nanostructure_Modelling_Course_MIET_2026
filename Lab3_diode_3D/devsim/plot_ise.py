# -*- coding: utf-8 -*-
"""ВАХ диодов A и B: DEVSIM с физикой ISE против ISE и эталона преподавателя.

    python plot_ise.py

Две панели:
  слева  — толщина 0.8 мкм (вариант 2), сетка ISE: проверка решателя против нашего прогона ISE;
  справа — толщина 2 мкм (базовая структура методички), сетка ISE, растянутая по z в 2.5 раза:
           против эталона преподавателя (reference/z2_вах.png, цифры — reference_iv.json).
Пишет ../results/devsim_ise/вах.png и печатает таблицы для README.
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
RED, BLACK = "#d62728", "#222222"


def load(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return None
    V, I = np.array(json.load(open(p))).T
    return V, np.abs(I)


def at(c, v):
    return float(np.interp(v, c[0], c[1])) if c is not None else float("nan")


def main():
    A8, B8 = load("iv_ise_A_isemesh_clip.json"), load("iv_ise_B_isemeshA_clip.json")
    A2, B2 = load("iv_ise_A_isemesh_lz2_clip.json"), load("iv_ise_B_isemeshA_lz2_clip.json")
    d = viz.read_plt(os.path.join(HERE, "..", "ise", "sA_des.plt"))
    ise = np.asarray(d["Anode OuterVoltage"]), np.abs(np.asarray(d["Anode TotalCurrent"]))
    ref = json.load(open(os.path.join(HERE, "reference_iv.json")))
    rA, rB = (np.array(ref[k]) for k in ("A", "B"))

    os.makedirs(OUT, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6), dpi=150, sharey=True)
    ax1.plot(ise[0], ise[1] * 1e3, "o", color=RED, ms=4, mfc="none", label="ISE, наш прогон, A")
    for c, col, name in ((A8, RED, "A"), (B8, BLACK, "B")):
        if c is not None:
            ax1.plot(c[0], c[1] * 1e3, color=col, lw=1.6, label="DEVSIM, физика ISE, " + name)
    ax1.set_title("толщина 0.8 мкм (вариант 2): проверка против ISE", fontsize=10)
    ax2.plot(rA[0], rA[1] * 1e3, color=RED, lw=6, alpha=0.25, label="эталон преподавателя, A")
    ax2.plot(rB[0], rB[1] * 1e3, color=BLACK, lw=6, alpha=0.25, label="эталон преподавателя, B")
    for c, col, name in ((A2, RED, "A"), (B2, BLACK, "B")):
        if c is not None:
            ax2.plot(c[0], c[1] * 1e3, color=col, lw=1.6, label="DEVSIM, физика ISE, " + name)
    ax2.set_title("толщина 2 мкм (база методички): против эталона", fontsize=10)
    for ax in (ax1, ax2):
        ax.set_xlim(0, 4); ax.set_ylim(0, 6)
        ax.set_xlabel("U, В"); ax.grid(ls=":", color="#999999")
        ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax1.set_ylabel("I, мА")
    fig.suptitle("Лаба 3: ВАХ диодов A и B, DEVSIM на сетке ISE", fontsize=11)
    fig.tight_layout()
    png = os.path.join(OUT, "вах.png")
    fig.savefig(png); print("картинка:", os.path.abspath(png))

    vs = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 3.95)
    print("\n0.8 мкм — против ISE:\n| U, В | A, мА | ISE A, мА | A/ISE | B, мА | B ниже A |")
    print("|---|---|---|---|---|---|")
    for v in vs:
        a, b, i = at(A8, v), at(B8, v), at(ise, v)
        print("| %.2f | %.3f | %.3f | %.3f | %.3f | %.0f %% |" % (v, a * 1e3, i * 1e3, a / i, b * 1e3, 100 * (1 - b / a)))
    print("\n2 мкм — против эталона:\n| U, В | A, мА | эталон A | A/эт | B, мА | эталон B | B/эт | B ниже A | эталон: B ниже A |")
    print("|---|---|---|---|---|---|---|---|---|")
    for v in vs:
        a, b, ra, rb = at(A2, v), at(B2, v), at(rA, v), at(rB, v)
        print("| %.2f | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f | %.0f %% | %.0f %% |"
              % (v, a * 1e3, ra * 1e3, a / ra, b * 1e3, rb * 1e3, b / rb, 100 * (1 - b / a), 100 * (1 - rb / ra)))


if __name__ == "__main__":
    main()
