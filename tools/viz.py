#!/usr/bin/env python3
"""Отрисовка результатов ISE TCAD в стиле Sentaurus Visual — на Plotly.

Оформление скопировано с эталонных рисунков в методичках:
белый фон, дискретные цветовые полосы от синего через зелёный к красному,
тонкий чёрный контур прибора, подписи осей X и Y снаружи, и главное —
ось Y направлена ВНИЗ (у диода анод с y = -d/2 оказывается сверху).

    import dfise, viz
    g = dfise.read_grid("sh1_msh.grd")
    d = dfise.read_dataset("sh1_des.dat", g)
    fig = viz.field_map(g, d["SpaceCharge"], "SpaceCharge", units="cm^-3")
    fig.write_html("charge.html")
"""
import re
import numpy as np
from matplotlib.tri import Triangulation, LinearTriInterpolator

# Радуга SVisual: тёмно-синий → синий → голубой → зелёный → жёлтый → оранжевый → красный
RAINBOW = [
    (0.00, "#00007f"), (0.12, "#0000ff"), (0.25, "#007fff"), (0.37, "#00ffff"),
    (0.50, "#00ff7f"), (0.62, "#7fff00"), (0.75, "#ffff00"), (0.87, "#ff7f00"),
    (1.00, "#ff0000"),
]

_AXIS = dict(showgrid=False, zeroline=False, ticks="outside", ticklen=6,
             linecolor="black", linewidth=1, mirror=False, color="black",
             tickfont=dict(size=15, color="black", family="serif"))


def read_plt(path):
    """Прочитать DF-ISE xyplot (.plt) — ВАХ, сечения, сигналы во времени."""
    txt = open(path, "r", errors="replace").read()
    names = re.findall(r'"([^"]+)"',
                       re.search(r"datasets\s*=\s*\[(.*?)\]", txt, re.S).group(1))
    body = txt[txt.index("Data {") + 6:]
    # файл может быть оборван, если расчёт не дошёл до конца — читаем что есть
    if "}" in body:
        body = body[:body.rindex("}")]
    vals = np.array([float(x) for x in body.split()])
    n = len(names)
    vals = vals[:len(vals) // n * n].reshape(-1, n)
    return {nm: vals[:, i] for i, nm in enumerate(names)}


def _boundary(grid, tri):
    """Рёбра, принадлежащие одному треугольнику, — внешний контур прибора."""
    cnt = {}
    for t in tri:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            cnt[(min(a, b), max(a, b))] = cnt.get((min(a, b), max(a, b)), 0) + 1
    return [e for e, c in cnt.items() if c == 1]


def field_map(grid, values, title="", units="", levels=16, res=420,
              show_mesh=False, show_contours=False, log=False, zrange=None,
              width=900):
    """Двумерная карта скалярного поля в оформлении SVisual."""
    import dfise
    V = grid["vertices"]
    tri = dfise.triangles(grid)
    x, y = V[:, 0], V[:, 1]
    z = np.asarray(values, dtype=float)

    if log:
        z = np.log10(np.abs(z) + 1e-30)

    good = ~np.isnan(z)
    zf = np.where(good, z, np.nanmean(z[good]))
    T = Triangulation(x, y, tri)
    interp = LinearTriInterpolator(T, zf)

    gx = np.linspace(x.min(), x.max(), res)
    gy = np.linspace(y.min(), y.max(), max(40, int(res * (np.ptp(y) / max(np.ptp(x), 1e-12)))))
    GX, GY = np.meshgrid(gx, gy)
    GZ = interp(GX, GY)                       # вне сетки — маска
    GZ = np.where(GZ.mask, np.nan, GZ.data) if np.ma.isMaskedArray(GZ) else GZ

    lo, hi = (np.nanmin(z), np.nanmax(z)) if zrange is None else zrange
    if hi <= lo:
        hi = lo + 1.0
    step = (hi - lo) / levels

    import plotly.graph_objects as go       # только для рисования: read_plt без plotly
    fig = go.Figure()
    fig.add_trace(go.Contour(
        x=gx, y=gy, z=GZ, colorscale=RAINBOW,
        contours=dict(start=lo, end=hi, size=step,
                      coloring="fill",
                      showlines=bool(show_contours)),
        line=dict(width=1, color="black") if show_contours else dict(width=0),
        colorbar=dict(title=dict(text=units, side="right"), thickness=14,
                      outlinecolor="black", outlinewidth=1,
                      tickfont=dict(size=11, family="serif")),
        hovertemplate="x=%{x:.4g}<br>y=%{y:.4g}<br>%{z:.4g}<extra></extra>",
    ))

    if show_mesh:
        mx, my = [], []
        for t in tri:
            for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                mx += [x[a], x[b], None]
                my += [y[a], y[b], None]
        fig.add_trace(go.Scatter(x=mx, y=my, mode="lines", hoverinfo="skip",
                                 line=dict(color="rgba(0,0,0,0.45)", width=0.4),
                                 showlegend=False))

    bx, by = [], []
    for a, b in _boundary(grid, tri):
        bx += [x[a], x[b], None]
        by += [y[a], y[b], None]
    fig.add_trace(go.Scatter(x=bx, y=by, mode="lines", hoverinfo="skip",
                             line=dict(color="black", width=1.2), showlegend=False))

    # Высота считается из пропорций прибора: SVisual сохраняет геометрию,
    # но не оставляет вокруг пустого поля. Жёсткий scaleanchor этого не даёт —
    # у вытянутого транзистора 15x2 он растянул бы картинку на пустоту.
    dx, dy = np.ptp(x), np.ptp(y)
    plot_w = width - 190
    height = int(plot_w * (dy / dx)) + 115
    height = max(260, min(height, 900))

    lbl = dict(size=17, family="serif", color="black")
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center",
                   font=dict(size=12, family="serif", color="black")),
        paper_bgcolor="white", plot_bgcolor="white", font=dict(color="black"),
        margin=dict(l=70, r=20, t=45, b=60), width=width, height=height,
        xaxis=dict(_AXIS, range=[x.min(), x.max()],
                   title=dict(text="X", font=lbl)),
        # ось Y вниз — так рисует SVisual разрезы приборов
        yaxis=dict(_AXIS, range=[y.max(), y.min()],
                   title=dict(text="Y", font=lbl)),
    )
    return fig


def xy_plot(curves, xlabel="", ylabel="", title="", logy=False):
    """График кривых: ВАХ, распределения в сечении, сигналы во времени.

    curves — список (подпись, x, y).
    """
    import plotly.graph_objects as go
    fig = go.Figure()
    for name, cx, cy in curves:
        fig.add_trace(go.Scatter(x=cx, y=cy, mode="lines", name=name,
                                 line=dict(width=2)))
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center",
                   font=dict(size=13, family="serif")),
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(l=80, r=25, t=50, b=60), width=820, height=560,
        xaxis=dict(_AXIS, title=dict(text=xlabel, font=dict(size=15, family="serif")),
                   showgrid=True, gridcolor="#e6e6e6"),
        yaxis=dict(_AXIS, title=dict(text=ylabel, font=dict(size=15, family="serif")),
                   showgrid=True, gridcolor="#e6e6e6",
                   type="log" if logy else "linear"),
        legend=dict(bgcolor="rgba(255,255,255,0.8)", bordercolor="black",
                    borderwidth=1, font=dict(size=12, family="serif")),
    )
    return fig
