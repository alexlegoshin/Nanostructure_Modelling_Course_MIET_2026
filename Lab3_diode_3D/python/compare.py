# -*- coding: utf-8 -*-
"""Сравнение ВАХ: питон против ISE (и эталона методички)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import viz

HERE = os.path.dirname(os.path.abspath(__file__))

def ise(f):
    d = viz.read_plt(f)
    V = np.asarray(d["Anode OuterVoltage"]); I = np.asarray(d["Anode TotalCurrent"])
    o = np.argsort(V); return V[o], I[o]

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
got = []
for tag, col, name in (("A", "tab:red", "диод A (полный анод)"),
                       ("B", "tab:blue", "диод B (половинный анод)")):
    f = os.path.join(HERE, "iv_%s.npz" % tag)
    if not os.path.exists(f): continue
    z = np.load(f); got.append((tag, z["V"], z["I"], col, name))
    for a in ax: a.plot(z["V"], z["I"], "-o", ms=3, color=col, label="питон, " + name)

for tag, col, style in (("A", "tab:red", "--"), ("B", "tab:blue", "--")):
    p = os.path.join(HERE, "..", "ise", "s%s_des.plt" % tag)
    if not os.path.exists(p): continue
    try:
        V, I = ise(p)
        if V.max() < 0.5: continue
        for a in ax: a.plot(V, I, style, color=col, lw=1.6, label="ISE, диод " + tag)
    except Exception: pass

for tag, col in (("A", "tab:red"), ("B", "tab:blue")):
    p = os.path.join(HERE, "..", "devsim", {"A": "iv_ise_A_isemesh_clip.json",
                                             "B": "iv_ise_B_isemeshA_clip.json"}[tag])
    if not os.path.exists(p): continue
    import json
    VI = np.array(json.load(open(p)))
    for a in ax: a.plot(VI[:, 0], VI[:, 1], ":", color=col, lw=2, label="DEVSIM (физика ISE), диод " + tag)

ax[0].set_xlabel("напряжение на аноде, В"); ax[0].set_ylabel("ток, А")
ax[0].set_title("линейная шкала"); ax[0].grid(alpha=.3); ax[0].legend(fontsize=8)
ax[1].set_yscale("log"); ax[1].set_xlabel("напряжение на аноде, В")
ax[1].set_title("логарифмическая шкала"); ax[1].grid(alpha=.3, which="both")
fig.tight_layout()
out = os.path.join(HERE, "..", "results", "вах_питон_против_ISE.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, dpi=130)
print("сохранено:", out)
for tag, V, I, _, _ in got:
    print("  питон, диод %s: до %.2f В, ток на конце %.5f А" % (tag, V.max(), I[-1]))
