# -*- coding: utf-8 -*-
"""3D-сетка ISE (DF-ISE .grd) целиком: тетраэдры, контакты, легирование в узлах.

Нужна, чтобы посчитать прибор другим решателем НА ТОЙ ЖЕ сетке, что и ISE:
тогда расхождение с ISE — это физика и численная схема, а не сетка.

Устройство 3D DF-ISE (то, чего нет в tools/dfise.py — там только поверхность):
  Edges   — пары вершин;
  Faces   — «3 e0 e1 e2»: треугольник из трёх рёбер (отрицательное — ребро наоборот, -(i+1));
  Elements:
    «5 f0 f1 f2 f3» — тетраэдр из четырёх граней (отрицательный индекс — грань наоборот),
    «2 e0 e1 e2»   — треугольник из трёх рёбер (контакты);
  Region  — материал и номера элементов.
"""
import re
import numpy as np

from dfise import _block, read_dataset


def _ints(body):
    return np.array(body.split(), dtype=np.int64)


def read_tet_grid(path):
    txt = open(path, "rb").read()
    vb, _ = _block(txt, txt.index(b"Vertices ("))
    verts = np.array(vb.split(), dtype=float).reshape(-1, 3)
    eb, _ = _block(txt, txt.index(b"Edges ("))
    edges = _ints(eb).reshape(-1, 2)

    fb, _ = _block(txt, txt.index(b"Faces ("))
    ftok = _ints(fb)
    faces, i = [], 0
    while i < len(ftok):
        n = int(ftok[i]); faces.append(ftok[i + 1:i + 1 + n]); i += 1 + n

    def edge_nodes(e):
        return edges[e] if e >= 0 else edges[-e - 1]

    def face_nodes(f):
        f = f if f >= 0 else -f - 1
        return {int(v) for e in faces[f] for v in edge_nodes(int(e))}

    ob, _ = _block(txt, txt.index(b"Elements ("))
    tok = _ints(ob)
    elems, i = [], 0
    while i < len(tok):
        t = int(tok[i])
        n = {2: 3, 5: 4}[t]                       # в 3D-сетке ISE других типов нет
        raw = tok[i + 1:i + 1 + n]; i += 1 + n
        if t == 5:
            nodes = set()
            for f in raw:
                nodes |= face_nodes(int(f))
        else:
            nodes = {int(v) for e in raw for v in edge_nodes(int(e))}
        if len(nodes) != {2: 3, 5: 4}[t]:
            raise ValueError("элемент %d собрался из %d вершин" % (len(elems), len(nodes)))
        elems.append((t, sorted(nodes)))

    regions = {}
    for m in re.finditer(rb'Region \("([^"]+)"\)', txt):
        body, _ = _block(txt, m.end())
        mat = re.search(rb"material\s*=\s*(\S+)", body).group(1).decode()
        ib, _ = _block(body, body.index(b"Elements"))
        regions[m.group(1).decode()] = (mat, _ints(ib))

    out = {"vertices": verts, "bulk": {}, "contacts": {}}
    for name, (mat, ids) in regions.items():
        arr = np.array([elems[k][1] for k in ids], dtype=np.int64)
        (out["contacts"] if mat == "Contact" else out["bulk"])[name] = (mat, arr)
    return out


def tet_volumes(verts, tets):
    a, b, c, d = (verts[tets[:, k]] for k in range(4))
    return np.abs(np.einsum("ij,ij->i", b - a, np.cross(c - a, d - a))) / 6.0


def load(grd, dat):
    """Сетка + легирование ISE: доноры (As) и акцепторы (B) в каждом узле, см^-3."""
    g = read_tet_grid(grd)
    d = read_dataset(dat)
    g["donors"] = d["ArsenicActiveConcentration"]
    g["acceptors"] = d["BoronActiveConcentration"]
    g["net"] = d["DopingConcentration"]
    return g


if __name__ == "__main__":
    import sys
    g = load(sys.argv[1], sys.argv[2])
    v = g["vertices"]
    print("узлов %d, габариты x %.3g..%.3g  y %.3g..%.3g  z %.3g..%.3g мкм"
          % (len(v), *[f(v[:, k]) for k in range(3) for f in (np.min, np.max)]))
    for name, (mat, t) in g["bulk"].items():
        print("  %-8s %-8s %6d тетраэдров, объём %.4f мкм³" % (name, mat, len(t), tet_volumes(v, t).sum()))
    for name, (mat, t) in g["contacts"].items():
        pts = v[np.unique(t)]
        print("  %-8s %-8s %6d треугольников, %d узлов, x %.3g..%.3g y %.3g..%.3g z %.3g..%.3g"
              % (name, mat, len(t), len(pts), *[f(pts[:, k]) for k in range(3) for f in (np.min, np.max)]))
    for k in ("donors", "acceptors", "net"):
        a = g[k]
        print("  %-9s мин %.3g  макс %.3g  уникальных %d" % (k, a.min(), a.max(), len(np.unique(a))))
