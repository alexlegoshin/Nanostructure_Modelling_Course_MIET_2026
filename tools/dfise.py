#!/usr/bin/env python3
"""Чтение файлов DF-ISE — формата, в котором ISE TCAD хранит сетку и поля.

    grid = read_grid("t_msh.grd")     # вершины, элементы, регионы
    data = read_dataset("t_des.dat")  # {имя поля: массив по вершинам}

Две особенности формата, из-за которых нельзя читать наивно:

1. Элементы задаются НЕ вершинами, а рёбрами. Отрицательный индекс ребра
   означает обратное направление, кодируется как -(i+1). Чтобы получить
   треугольник или четырёхугольник, надо обойти рёбра и собрать кольцо вершин.

2. Поле может храниться не одним массивом на всю сетку, а отдельным блоком
   на каждый регион (`validity = ["S10"]`). Тогда значения идут в порядке
   возрастания глобальных индексов вершин этого региона, и блоки надо сшивать.
"""
import re
import numpy as np

_NUM = re.compile(rb"[-+0-9.eE]+")


def _block(txt, start):
    """Вернуть содержимое {...}, начиная от позиции первой открывающей скобки."""
    i = txt.index(b"{", start)
    depth = 0
    for j in range(i, len(txt)):
        c = txt[j]
        if c == 0x7B:
            depth += 1
        elif c == 0x7D:
            depth -= 1
            if depth == 0:
                return txt[i + 1:j], j
    raise ValueError("незакрытая скобка")


def read_grid(path):
    txt = open(path, "rb").read()
    info, _ = _block(txt, txt.index(b"Info"))
    dim = int(re.search(rb"dimension\s*=\s*(\d+)", info).group(1))
    regions = re.findall(rb'"([^"]+)"', re.search(rb"regions\s*=\s*\[([^\]]*)\]", info).group(1))
    mats = re.search(rb"materials\s*=\s*\[([^\]]*)\]", info).group(1).split()

    vb, _ = _block(txt, txt.index(b"Vertices"))
    verts = np.array([float(x) for x in vb.split()]).reshape(-1, dim)

    eb, _ = _block(txt, txt.index(b"Edges"))
    edges = np.array([int(x) for x in eb.split()]).reshape(-1, 2)

    ob, _ = _block(txt, txt.index(b"Elements ("))
    tok = [int(x) for x in ob.split()]

    elems, i = [], 0
    while i < len(tok):
        t = tok[i]
        # 0 — точка (одна вершина), 1 — отрезок, 2 — треугольник, 3 — четырёхугольник.
        # Точки появляются в сечениях 3D-приборов: контакт, пересечённый плоскостью
        # по касательной, вырождается в одну вершину.
        n = {0: 1, 1: 2, 2: 3, 3: 4}.get(t)
        if n is None:                      # 3D-типы здесь не разбираем
            break
        raw = tok[i + 1:i + 1 + n]
        i += 1 + n
        if t == 0:
            elems.append(("point", raw))
            continue
        if t == 1:
            elems.append(("line", raw))
            continue
        ring = []
        for e in raw:
            a, b = edges[e] if e >= 0 else edges[-e - 1][::-1]
            if not ring:
                ring += [int(a), int(b)]
            elif ring[-1] == a:
                ring.append(int(b))
            elif ring[-1] == b:
                ring.append(int(a))
            else:                          # ребро не стыкуется — кольцо битое
                ring.append(int(a))
        if ring and ring[0] == ring[-1]:
            ring.pop()
        elems.append(("tri" if t == 2 else "quad", ring))

    reg = {}
    for m in re.finditer(rb'Region \("([^"]+)"\)', txt):
        name = m.group(1).decode()
        body, _ = _block(txt, m.end())
        mat = re.search(rb"material\s*=\s*(\S+)", body)
        idx_body, _ = _block(body, body.index(b"Elements"))
        reg[name] = {
            "material": mat.group(1).decode() if mat else "",
            "elements": [int(x) for x in idx_body.split()],
        }

    return {"dim": dim, "vertices": verts, "edges": edges,
            "elements": elems, "regions": reg,
            "region_order": [r.decode() for r in regions],
            "materials": [m.decode() for m in mats]}


def read_dataset(path, grid=None):
    """Прочитать поля. Блоки, размеченные по регионам, сшиваются в общий массив."""
    txt = open(path, "rb").read()
    info, _ = _block(txt, txt.index(b"Info"))
    nv = int(re.search(rb"nb_vertices\s*=\s*(\d+)", info).group(1))

    out, pos = {}, 0
    while True:
        m = re.compile(rb'Dataset \("([^"]+)"\)').search(txt, pos)
        if not m:
            break
        name = m.group(1).decode()
        body, end = _block(txt, m.end())
        pos = end

        kind = re.search(rb"type\s*=\s*(\w+)", body)
        kind = kind.group(1).decode() if kind else "scalar"
        dim = re.search(rb"dimension\s*=\s*(\d+)", body)   # у dessis вектор — только dimension = 3
        if dim and int(dim.group(1)) > 1:
            kind = "vector"
        valid = re.findall(rb'"([^"]+)"', re.search(rb"validity\s*=\s*\[([^\]]*)\]", body).group(1))
        vb, _ = _block(body, body.index(b"Values"))
        vals = np.array([float(x) for x in vb.split()])

        if kind == "vector":
            comp = int(re.search(rb"dimension\s*=\s*(\d+)", body).group(1))
            vals = vals.reshape(-1, comp)

        if name not in out:
            shape = (nv,) if kind == "scalar" else (nv, vals.shape[1])
            out[name] = np.full(shape, np.nan)

        if len(vals) == nv:
            out[name][:] = vals
        elif grid is not None and len(valid) == 1:
            rname = valid[0].decode()
            vids = _region_vertices(grid, rname)
            if len(vids) == len(vals):
                out[name][vids] = vals
    return out


def _region_vertices(grid, rname):
    """Отсортированные глобальные индексы вершин региона."""
    got = set()
    for ei in grid["regions"][rname]["elements"]:
        got.update(grid["elements"][ei][1])
    return np.array(sorted(got), dtype=int)


def triangles(grid):
    """Все элементы как треугольники — четырёхугольники режутся пополам."""
    tri = []
    for kind, ring in grid["elements"]:
        if kind == "tri" and len(ring) == 3:
            tri.append(ring)
        elif kind == "quad" and len(ring) == 4:
            tri.append([ring[0], ring[1], ring[2]])
            tri.append([ring[0], ring[2], ring[3]])
    return np.array(tri, dtype=int)


def read_grid3d(path):
    """3D-сетка: вершины и ТОЛЬКО внешние грани.

    В DF-ISE грань задаётся рёбрами (отрицательный индекс — ребро наоборот),
    а блок Locations помечает каждую грань как внутреннюю `i` или внешнюю `e`.
    Для картинки прибора нужны только внешние — из них и состоит поверхность.
    """
    txt = open(path, "rb").read()

    vb, _ = _block(txt, txt.index(b"Vertices ("))
    verts = np.array([float(x) for x in vb.split()]).reshape(-1, 3)

    eb, _ = _block(txt, txt.index(b"Edges ("))
    edges = np.array([int(x) for x in eb.split()]).reshape(-1, 2)

    fb, _ = _block(txt, txt.index(b"Faces ("))
    tok = [int(x) for x in fb.split()]
    faces, i = [], 0
    while i < len(tok):
        n = tok[i]
        faces.append(tok[i + 1:i + 1 + n])
        i += 1 + n

    lb, _ = _block(txt, txt.index(b"Locations ("))
    loc = lb.split()

    tri = []
    for f, where in zip(faces, loc):
        if where != b"e" or len(f) != 3:
            continue
        ring = []
        for e in f:
            a, b = edges[e] if e >= 0 else edges[-e - 1][::-1]
            if not ring:
                ring += [int(a), int(b)]
            elif ring[-1] == a:
                ring.append(int(b))
            else:
                ring.append(int(a))
        if len(ring) > 3 and ring[0] == ring[-1]:
            ring.pop()
        if len(ring) == 3:
            tri.append(ring)
    return {"vertices": verts, "surface": np.array(tri, dtype=int)}


def read_tets3d(path):
    """Тетраэдры 3D-сетки как четвёрки вершин (для интерполяции поля на сечение).

    Элемент типа 5 задан четырьмя гранями (отрицательный индекс — грань наоборот,
    -f-1), грань — рёбрами; вершины тетраэдра — объединение вершин его граней.
    """
    txt = open(path, "rb").read()
    eb, _ = _block(txt, txt.index(b"Edges ("))
    edges = np.array([int(x) for x in eb.split()]).reshape(-1, 2)
    fb, _ = _block(txt, txt.index(b"Faces ("))
    tok = [int(x) for x in fb.split()]
    fverts, i = [], 0
    while i < len(tok):
        n = tok[i]
        fverts.append({int(v) for e in tok[i + 1:i + 1 + n]
                       for v in (edges[e] if e >= 0 else edges[-e - 1])})
        i += 1 + n
    lb, _ = _block(txt, txt.index(b"Elements ("))
    tok = [int(x) for x in lb.split()]
    size = {1: 2, 2: 3, 3: 4, 5: 4, 6: 5, 7: 5, 8: 6}     # число граней/вершин по типу DF-ISE
    tets, i = [], 0
    while i < len(tok):
        kind = tok[i]; n = size[kind]
        if kind == 5:
            vs = set().union(*(fverts[f if f >= 0 else -f - 1] for f in tok[i + 1:i + 1 + n]))
            tets.append(sorted(vs))
        i += 1 + n
    return np.array(tets)
