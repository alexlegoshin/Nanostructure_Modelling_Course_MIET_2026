# -*- coding: utf-8 -*-
"""Три картинки в ряд: эталон из методички, наша отрисовка, вывод picasso.

Эталоны лежат в Lab*/reference/ — они вырезаны прямо из файла вариантов методички
(в .doc картинки хранятся как обычные PNG, достаются поиском сигнатуры).
В репозитории только эталоны варианта 2.
"""

import os
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ref(variant, name):
    """Путь к эталонной картинке: ref(2, 'z1_заряд'). Ищется по всем лабам."""
    import glob
    hits = glob.glob(os.path.join(ROOT, "Lab*", "reference", name + ".png"))
    return hits[0] if hits else None


def pic(name):
    """Путь к картинке из picasso, если она есть."""
    p = os.path.join(ROOT, "picasso", name + ".png")
    return p if os.path.exists(p) else None


def trio(ref_path, our_path, pic_path=None, width=9.0):
    """Эталон сверху, наша отрисовка под ним, picasso третьей (если есть)."""
    items = [("эталон из методички", ref_path), ("наша отрисовка", our_path)]
    if pic_path:
        items.append(("picasso, родная отрисовка", pic_path))
    items = [(t, p) for t, p in items if p and os.path.exists(p)]

    imgs = [mpimg.imread(p) for _, p in items]
    hs = [im.shape[0] / im.shape[1] for im in imgs]          # высота на единицу ширины
    fig, axes = plt.subplots(len(imgs), 1,
                             figsize=(width, width * sum(hs) + 0.42 * len(imgs)))
    if len(imgs) == 1:
        axes = [axes]
    for ax, im, (title, _) in zip(axes, imgs, items):
        ax.imshow(im)
        ax.set_title(title, fontsize=10, loc="left", color="#444")
        ax.set_axis_off()
    fig.tight_layout()
    return fig
