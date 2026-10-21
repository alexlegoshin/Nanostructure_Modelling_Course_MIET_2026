# -*- coding: utf-8 -*-
"""ВАХ диодов A и B: DEVSIM с физикой ISE против ISE и эталона варианта 2.

    python plot_ise.py

Две панели, обе — толщина 0.8 мкм (вариант 2), сетка ISE:
  слева  — проверка решателя против нашего прогона ISE (оба диода);
  справа — против эталона варианта 2 (reference/z2_вах.png, цифры — reference_iv.json).
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
    def ise_iv(t):
        d = viz.read_plt(os.path.join(HERE, "..", "ise", "s%s_des.plt" % t))
        return np.asarray(d["Anode OuterVoltage"]), np.abs(np.asarray(d["Anode TotalCurrent"]))
    ise, iseB = ise_iv("A"), ise_iv("B")
    ref = json.load(open(os.path.join(HERE, "reference_iv.json")))
    rA, rB = (np.array(ref[k]) for k in ("A", "B"))

    os.makedirs(OUT, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6), dpi=150, sharey=True)
    ax1.plot(ise[0], ise[1] * 1e3, "o", color=RED, ms=4, mfc="none", label="ISE, A")
    ax1.plot(iseB[0], iseB[1] * 1e3, "s", color=BLACK, ms=3.5, mfc="none", label="ISE, B")
    ax2.plot(rA[0], rA[1] * 1e3, color=RED, lw=6, alpha=0.25, label="эталон варианта 2, A")
    ax2.plot(rB[0], rB[1] * 1e3, color=BLACK, lw=6, alpha=0.25, label="эталон варианта 2, B")
    for ax in (ax1, ax2):
        for c, col, name in ((A8, RED, "A"), (B8, BLACK, "B")):
            if c is not None:
                ax.plot(c[0], c[1] * 1e3, color=col, lw=1.6, label="DEVSIM, " + name)
    ax1.set_title("DEVSIM против ISE", fontsize=10)
    ax2.set_title("DEVSIM против эталона варианта 2", fontsize=10)
    for ax in (ax1, ax2):
        ax.set_xlim(0, 4); ax.set_ylim(0, 6)
        ax.set_xlabel("U, В"); ax.grid(ls=":", color="#999999")
        ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax1.set_ylabel("I, мА")
    fig.suptitle("Лаба 3: ВАХ диодов A и B, толщина 0.8 мкм", fontsize=11)
    fig.tight_layout()
    png = os.path.join(OUT, "вах.png")
    fig.savefig(png); print("картинка:", os.path.abspath(png))

    vs = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 3.95)
    print("\n| U, В | A, мА | ISE A | эталон A | B, мА | ISE B | эталон B | B ниже A | эталон: B ниже A |")
    print("|---|---|---|---|---|---|---|---|---|")
    for v in vs:
        a, b, i, ib, ra, rb = at(A8, v), at(B8, v), at(ise, v), at(iseB, v), at(rA, v), at(rB, v)
        print("| %.2f | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f | %.1f %% | %.1f %% |"
              % (v, a * 1e3, i * 1e3, ra * 1e3, b * 1e3, ib * 1e3, rb * 1e3, 100 * (1 - b / a), 100 * (1 - rb / ra)))


if __name__ == "__main__":
    main()
