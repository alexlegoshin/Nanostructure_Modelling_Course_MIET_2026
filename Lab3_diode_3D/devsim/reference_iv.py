# -*- coding: utf-8 -*-
"""ВАХ преподавателя (эталон методички) — цифрами, снятыми с reference/z2_вах.png.

Красная кривая — диод A, чёрная — диод B. Оси калибруются по линиям сетки самой
картинки (пунктир 1, 2, 3 В и 0.002, 0.004 А) и по рамке (0 В, 4 В, 0 А).
Чёрный цвет есть и у подписей, поэтому кривая B берётся только внутри поля графика.

    python reference_iv.py          # пишет reference_iv.json и печатает таблицу
"""
import json, os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PNG = os.path.join(HERE, "..", "reference", "z2_вах.png")


def axes(img):
    """Пиксели рамки и линий сетки: x (0..4 В) и y (0, 0.002, 0.004 А)."""
    a = np.asarray(img.convert("RGB")).astype(int)
    dark = (a.sum(axis=2) < 200)
    rows, cols = dark.sum(axis=1), dark.sum(axis=0)
    # рамка — самые длинные сплошные линии
    left = int(np.argmax(cols[: a.shape[1] // 2]))
    right = a.shape[1] // 2 + int(np.argmax(cols[a.shape[1] // 2:]))
    bottom = a.shape[0] // 2 + int(np.argmax(rows[a.shape[0] // 2:]))
    # пунктир сетки: серые/чёрные точки через одну — ищем столбцы и строки с частыми тёмными точками
    gx = [c for c in range(left + 5, right - 4) if dark[:bottom, c].sum() > 0.25 * (bottom)]
    gy = [r for r in range(5, bottom - 4) if dark[r, left:right].sum() > 0.25 * (right - left)]
    return a, left, right, bottom, gx, gy


def group(v):
    out, cur = [], [v[0]]
    for x in v[1:]:
        if x - cur[-1] <= 2:
            cur.append(x)
        else:
            out.append(np.mean(cur)); cur = [x]
    return out + [np.mean(cur)]


def main():
    img = Image.open(PNG)
    a, left, right, bottom, gx, gy = axes(img)
    gx, gy = group(gx), [g for g in group(gy) if g > 12]      # верхняя рамка — не линия сетки
    print("рамка: x %d..%d, низ %d; линии сетки x %s, y %s" % (left, right, bottom, gx, gy))
    # 0 В — левая рамка, 1/2/3 В — пунктиры, 4 В — правая рамка
    xs = np.array([left] + gx + [right]); xv = np.arange(len(xs), dtype=float)
    # 0 А — нижняя рамка, 0.002 и 0.004 А — пунктиры (сверху вниз: 0.004, 0.002)
    ys = np.array([bottom] + sorted(gy, reverse=True)); yv = np.arange(len(ys)) * 0.002
    kx = np.polyfit(xs, xv, 1); ky = np.polyfit(ys, yv, 1)
    print("масштаб: %.5f В/пикс (невязка %.1e), %.3e А/пикс (невязка %.1e)"
          % (kx[0], np.abs(np.polyval(kx, xs) - xv).max(), ky[0], np.abs(np.polyval(ky, ys) - yv).max()))

    red = (a[:, :, 0] > 180) & (a[:, :, 1] < 80) & (a[:, :, 2] < 80)
    black = (a.sum(axis=2) < 150)
    out = {}
    for name, mask in (("A", red), ("B", black)):
        V, I = [], []
        for c in range(left + 2, right - 1):
            if name == "B" and any(abs(c - g) <= 2 for g in gx):
                continue                                         # вертикальный пунктир сетки
            r = np.where(mask[:bottom - 1, c])[0]
            if name == "B":
                r = r[(r > 9)]                                   # верхняя рамка (строка 6)
                # пунктир сетки и подписи тоже чёрные: берём самый верхний чёрный пиксель,
                # который не на линии сетки
                r = [x for x in r if all(abs(x - g) > 1.5 for g in gy)]
            if len(r):
                V.append(np.polyval(kx, c)); I.append(np.polyval(ky, np.mean(r[:3])))
        out[name] = (np.array(V), np.array(I))

    tab = {}
    print("\n  V     A, мА    B, мА    B/A")
    for v in (0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 3.95):
        ia, ib = (np.interp(v, *out[k]) for k in ("A", "B"))
        tab[v] = (ia, ib)
        print("  %.2f  %6.3f   %6.3f   %.3f" % (v, ia * 1e3, ib * 1e3, ib / ia))
    json.dump({k: [list(map(float, v)), list(map(float, i))] for k, (v, i) in out.items()},
              open(os.path.join(HERE, "reference_iv.json"), "w"))


if __name__ == "__main__":
    main()
