# -*- coding: utf-8 -*-
"""Развёртка по напряжению своим 3D-решателем (tools/dd3d.py), пишет результат в .npz.

    python3 sweep.py "[0,1,1,2]"   A 10 14 9 4     # диод A, полный анод
    python3 sweep.py "[0.5,1,1,2]" B 10 14 9 4     # диод B, половинный анод

Аргументы: анод (x0,y0,x1,y1) в мкм, метка, базовое число узлов по x/y/z, Vmax.
"""
import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import numpy as np
import dd3d

anode = tuple(json.loads(sys.argv[1])) if len(sys.argv) > 1 else (0.0, 1.0, 1.0, 2.0)
tag   = sys.argv[2] if len(sys.argv) > 2 else "A"
nx, ny, nz = (int(v) for v in (sys.argv[3:6] or (10, 14, 9)))
Vmax = float(sys.argv[6]) if len(sys.argv) > 6 else 4.0

d = dd3d.Diode(anode=anode, nx=nx, ny=ny, nz=nz)
print("диод %s: сетка %dx%dx%d = %d узлов" % (tag, d.nx, d.ny, d.nz, d.N), flush=True)

volts = np.concatenate([np.arange(0.0, 1.0, 0.2), np.arange(1.0, Vmax + 1e-9, 0.25)])
state, Is, Vs = None, [], []
t0 = time.time()
for V in volts:
    state, n, p, I, k = d.gummel(float(V), state=state, outer=25, tol=3e-4)
    Is.append(I); Vs.append(float(V))
    print("  V=%.2f  I=%.5e А   (%d итераций, %.0f с)" % (V, I, k, time.time() - t0), flush=True)
    np.savez(os.path.join(os.path.dirname(__file__), "iv_%s.npz" % tag),
             V=np.array(Vs), I=np.array(Is))
np.savez(os.path.join(os.path.dirname(__file__), "field_%s.npz" % tag),
         psi=state[0], n=n, p=p, x=d.x, y=d.y, z=d.z, C=d.C)
print("готово за %.0f с" % (time.time() - t0), flush=True)
