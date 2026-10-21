# -*- coding: utf-8 -*-
"""Отрисовка в стиле ISE TCAD 7.0 (picasso / inspect).

Палитра, геометрия рамки, направление и частота засечек сняты пиксельно
с эталонных картинок, вшитых в Variants_1-2_2023.doc. Цель — чтобы
результат не отличался от того, что показывают родные программы.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
from matplotlib.ticker import AutoMinorLocator, FuncFormatter, MaxNLocator

import dfise

# 31 уровень, порядок от минимума к максимуму. Снято с эталона.
PALETTE = [
    (0, 42, 255), (0, 93, 255), (0, 128, 255), (0, 170, 255), (0, 191, 255),
    (0, 217, 255), (0, 234, 255), (0, 251, 255), (0, 255, 238), (0, 255, 221),
    (0, 255, 196), (0, 255, 174), (0, 255, 149), (0, 255, 102), (0, 255, 51),
    (59, 255, 0), (102, 255, 0), (153, 255, 0), (174, 255, 0), (196, 255, 0),
    (226, 255, 0), (238, 255, 0), (255, 247, 0), (255, 234, 0), (255, 217, 0),
    (255, 187, 0), (255, 166, 0), (255, 123, 0), (255, 85, 0), (255, 4, 0),
    (153, 0, 0),
]
RGB = [(r / 255, g / 255, b / 255) for r, g, b in PALETTE]
MAGENTA = (1.0, 0.0, 1.0)
JUNCTION = (153 / 255, 0.0, 0.0)      # линия p-n перехода, снята с эталона

MONO = ["DejaVu Sans Mono", "Courier New", "monospace"]


# ----------------------------------------------------------------- служебное

def _tri(grid):
    v = grid["vertices"]
    return Triangulation(v[:, 0], v[:, 1], dfise.triangles(grid))


def _contacts(grid):
    """Отрезки контактов как пары индексов вершин."""
    out = []
    for name in grid["region_order"]:
        r = grid["regions"][name]
        if r["material"] != "Contact":
            continue
        for e in r["elements"]:
            kind, ring = grid["elements"][e]
            if kind == "line" and len(ring) == 2:
                out.append((name, ring))
    return out


# Заряд меняется на полтора десятка порядков и меняет знак, поэтому picasso
# кладёт его на ареасинус: у нуля функция линейна, на хвостах логарифмична.
# В мануале это команда
#     device interpol <набор> linear | log | arsinh [фактор]
# Ключевое слово там именно interpol: преобразуются значения В УЗЛАХ, а
# интерполяция внутри треугольника идёт уже в преобразованных координатах,
# и только потом результат режется на равные полосы. Если сначала
# интерполировать по значению, а полосы считать по логарифму, картинка
# заметно краснее — проверено на эталонах.
ARSINH_A = 10 ** 13.95


def _t(z, a=ARSINH_A):
    return np.arcsinh(np.asarray(z, dtype=float) / a)


def _levels(vals, n=31):
    lo, hi = float(np.nanmin(vals)), float(np.nanmax(vals))
    if hi <= lo:
        hi = lo + 1.0
    return np.linspace(lo, hi, n + 1)


def _device_axes(grid, width):
    """Фигура под прибор: без осей, Y перевёрнута, поля как в эталоне."""
    v = grid["vertices"]
    x0, x1 = float(v[:, 0].min()), float(v[:, 0].max())
    y0, y1 = float(v[:, 1].min()), float(v[:, 1].max())
    asp = (x1 - x0) / (y1 - y0)
    height = width / asp
    fig = plt.figure(figsize=(width / 100.0, height / 100.0), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    mx = (x1 - x0) * 0.004
    my = (y1 - y0) * 0.004
    ax.set_xlim(x0 - mx, x1 + mx)
    ax.set_ylim(y1 + my, y0 - my)          # анод сверху, как в SVisual
    ax.set_axis_off()
    return fig, ax, (x0, x1, y0, y1)


def _junction(ax, grid, doping):
    """Линия p-n перехода — там, где суммарное легирование меняет знак.
    picasso рисует её отдельным объектом (Junctions), поверх заливки."""
    if doping is None:
        return
    tri = _tri(grid)
    ax.tricontour(tri, doping, levels=[0.0], colors=[JUNCTION],
                  linewidths=2.0, zorder=8)


def _frame_and_contacts(ax, grid, box):
    x0, x1, y0, y1 = box
    v = grid["vertices"]
    for _, (a, b) in _contacts(grid):
        ax.plot(v[[a, b], 0], v[[a, b], 1], color=MAGENTA, lw=2.2,
                solid_capstyle="butt", zorder=7)
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0],
            color="k", lw=1.4, zorder=6)


# ------------------------------------------------------------------ картинки

def field(grid, vals, path, mesh=False, width=578, log=False, doping=None):
    """Заливка поля дискретной радугой. mesh=True — поверх чёрная сетка.
    log=True — знаковая логарифмическая шкала (для плотности заряда)."""
    fig, ax, box = _device_axes(grid, width)
    tri = _tri(grid)
    if log:
        f = _t(vals)                       # интерполируем преобразованное поле
        lv = np.linspace(float(f.min()), float(f.max()), len(RGB) + 1)
    else:
        f, lv = vals, _levels(vals)
    ax.tricontourf(tri, f, levels=lv, colors=RGB, extend="both")
    if mesh:
        ax.triplot(tri, color="k", lw=0.7)
    _junction(ax, grid, doping)
    _frame_and_contacts(ax, grid, box)
    fig.savefig(path, dpi=100, facecolor="white")
    plt.close(fig)
    return path


def contour(grid, vals, path, width=578, doping=None):
    """Только линии уровня на белом, раскрашенные по значению."""
    fig, ax, box = _device_axes(grid, width)
    tri = _tri(grid)
    lv = _levels(vals)[1:-1]
    ax.tricontour(tri, vals, levels=lv, colors=RGB[1:len(lv) + 1], linewidths=1.0)
    _junction(ax, grid, doping)
    _frame_and_contacts(ax, grid, box)
    fig.savefig(path, dpi=100, facecolor="white")
    plt.close(fig)
    return path


# ---------------------------------------------------------------- XY-графики

def _fmt(v, _=None):
    if v == 0:
        return "0"
    a = abs(v)
    if 1e-3 <= a < 1e5:
        s = ("%.10f" % v).rstrip("0").rstrip(".")
        return s
    e = int(np.floor(np.log10(a)))
    m = v / (10.0 ** e)
    ms = ("%.10f" % m).rstrip("0").rstrip(".")
    return "%se%s%03d" % (ms, "+" if e >= 0 else "-", abs(e))


def xy(series, path, size=(465, 373), xlim=None, ylim=None, legend=True):
    """series — список (подпись, x, y, цвет). Оси и легенда как в inspect.

    Поля рамки считаются в пикселях, как в эталоне: слева ровно столько,
    сколько занимает самая длинная подпись, справа — место под легенду.
    """
    W, H = size
    fig = plt.figure(figsize=(W / 100.0, H / 100.0), dpi=100)
    ax = fig.add_axes([0.2, 0.1, 0.7, 0.85])

    for lab, x, y, col in series:
        ax.plot(x, y, color=col, lw=1.0, label=lab)

    if xlim: ax.set_xlim(*xlim)
    if ylim: ax.set_ylim(*ylim)

    ax.xaxis.set_major_locator(MaxNLocator(nbins=5, steps=[1, 2, 2.5, 5, 10]))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4, steps=[1, 2, 2.5, 5, 10]))
    ax.xaxis.set_minor_locator(AutoMinorLocator(4))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.xaxis.set_major_formatter(FuncFormatter(_fmt))
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt))
    ax.tick_params(which="major", direction="out", length=7, width=1.1,
                   top=False, right=False, labelsize=9)
    ax.tick_params(which="minor", direction="out", length=4, width=1.0,
                   top=False, right=False)
    for sp in ax.spines.values():
        sp.set_linewidth(1.1); sp.set_color("k")
    for t in ax.get_xticklabels() + ax.get_yticklabels():
        t.set_fontfamily(MONO); t.set_fontweight("bold")

    # поля под реальную длину подписей
    fig.canvas.draw()
    ylab = max((len(t.get_text()) for t in ax.get_yticklabels()), default=1)
    left = 20 + 7.5 * ylab
    right = 112 if legend else 12
    top, bottom = 5, 33
    ax.set_position([left / W, bottom / H,
                     (W - left - right) / W, (H - top - bottom) / H])

    if legend and any(l for l, *_ in series):
        lg = ax.legend(loc="upper left", bbox_to_anchor=(1.015, 1.0),
                       frameon=True, handlelength=1.4, borderpad=0.35,
                       handletextpad=0.5, labelspacing=0.3, fontsize=7.5)
        lg.get_frame().set_edgecolor("k"); lg.get_frame().set_linewidth(1.0)
        for t in lg.get_texts():
            t.set_fontfamily(MONO); t.set_fontweight("bold")

    fig.savefig(path, dpi=100, facecolor="white")
    plt.close(fig)
    return path


# ------------------------------------------------------- графики лабы 3 (inspect)
COURIER = ["Courier New", "Courier", "DejaVu Sans Mono", "monospace"]
HELV = ["Helvetica", "Arial", "DejaVu Sans"]
PX = 0.72                                   # 1 пиксель в пунктах при dpi = 100


def xy_ref(series, path, size, frame, xlabel, ylabel, xstep, ystep,
           xfmt="{:g}", yfmt="{:g}", xlim=None, ylim=None, ylabel_x=12, xlabel_y=None):
    """График в стиле эталонов лабы 3 (inspect): рамка в заданных пикселях, оси ровно
    по данным, пунктирная сетка по основным засечкам, засечки наружу, по 4 коротких
    между основными, линии в 2 пикселя без сглаживания.

    series — список (x, y, цвет); frame = (левый, правый, верхний, нижний) край рамки, px;
    xlabel — пара (величина, единица) — в эталоне между ними большой пробел.
    """
    W, H = size
    l, r, t, b = frame
    fig = plt.figure(figsize=((W + 0.1) / 100.0, (H + 0.1) / 100.0), dpi=100)   # без округления вниз
    ax = fig.add_axes([l / W, 1 - b / H, (r - l) / W, (b - t) / H])
    xs = np.concatenate([np.asarray(s[0], float) for s in series])
    ys = np.concatenate([np.asarray(s[1], float) for s in series])
    for x, y, col in series:
        ax.plot(x, y, color=col, lw=2 * PX, antialiased=False, solid_joinstyle="miter")
    ax.set_xlim(*(xlim or (xs.min(), xs.max())))
    ax.set_ylim(*(ylim or (ys.min(), ys.max())))
    from matplotlib.ticker import MultipleLocator
    ax.xaxis.set_major_locator(MultipleLocator(xstep))
    ax.yaxis.set_major_locator(MultipleLocator(ystep))
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: xfmt.format(v) if abs(v) > 1e-12 else "0"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: yfmt.format(v) if abs(v) > 1e-12 else "0"))
    ax.tick_params(which="major", direction="out", length=8 * PX, width=1.5 * PX,
                   top=False, right=False, labelsize=13, pad=5 * PX)
    ax.tick_params(which="minor", direction="out", length=5 * PX, width=1.5 * PX,
                   top=False, right=False)
    ax.grid(True, which="major", color="k", lw=1 * PX, ls=(0, (3, 3)))
    for sp in ax.spines.values():
        sp.set_linewidth(2 * PX); sp.set_color("k")
    for tl in ax.get_xticklabels() + ax.get_yticklabels():
        tl.set_fontfamily(COURIER); tl.set_fontweight("bold")
    # подписи осей — в тех же местах, что у inspect
    fig.text(ylabel_x / W, 1 - (t + b) / 2 / H, ylabel, rotation=90, ha="center", va="center",
             fontfamily=HELV, fontweight="bold", fontsize=17)
    q, u = xlabel
    yb = (xlabel_y if xlabel_y is not None else b + 50) / H
    cx = (l + r) / 2 / W
    fig.text(cx - 0.05, 1 - yb, q, ha="right", va="center", fontfamily=COURIER, fontweight="bold", fontsize=13)
    fig.text(cx + 0.03, 1 - yb, "(%s)" % u, ha="left", va="center", fontfamily=COURIER, fontweight="bold", fontsize=13)
    fig.savefig(path, dpi=100, facecolor="white")
    plt.close(fig)
    return path
