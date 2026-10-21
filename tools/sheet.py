# -*- coding: utf-8 -*-
"""Сводный лист: эталон и наша картинка парами, с подписями."""

import os
from PIL import Image, ImageDraw, ImageFont


def _font(size, bold=False):
    import matplotlib
    mpl = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
    paths = (["/System/Library/Fonts/Supplemental/Arial Bold.ttf", os.path.join(mpl, "DejaVuSans-Bold.ttf")] if bold else
             ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc",
              os.path.join(mpl, "DejaVuSans.ttf")])
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()


def pairs(items, path, title="", cell=(430, 330), pad=14):
    """items — список (подпись, путь к эталону, путь к нашему)."""
    CW, CH = cell
    head = 18 + 26 * len(title.split("\n")) if title else 10      # под любое число строк
    cap, sub = 22, 18
    rowh = CH + cap + sub + pad
    W = CW * 2 + pad * 3
    H = head + rowh * len(items) + pad

    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    f_t, f_c, f_s = _font(22), _font(15), _font(13)
    if title:
        for i, line in enumerate(title.split("\n")):
            d.text((pad, 12 + i * 26), line, fill="black", font=f_t)

    for r, item in enumerate(items):
        name, ref, our = item[0], item[1], item[2]
        note = item[3] if len(item) > 3 else ""
        y = head + r * rowh
        d.text((pad, y), name, fill="black", font=f_c)
        if note:
            w = d.textlength(name, font=f_c)
            d.text((pad + w + 14, y + 2), note, fill="#c40", font=f_s)
        for c, (lab, p) in enumerate((("эталон", ref), ("наш расчёт", our))):
            x = pad + c * (CW + pad)
            d.text((x, y + cap - 2), lab, fill="#a00" if c == 0 else "#06a", font=f_s)
            if not (p and os.path.exists(p)):
                d.text((x, y + cap + sub + 10), "нет файла", fill="#999", font=f_s)
                continue
            pic = Image.open(p).convert("RGB")
            s = min(CW / pic.width, CH / pic.height, 1.6)
            pic = pic.resize((max(1, int(pic.width * s)), max(1, int(pic.height * s))))
            im.paste(pic, (x + (CW - pic.width) // 2, y + cap + sub))
        d.line([(pad, y + rowh - pad // 2), (W - pad, y + rowh - pad // 2)], fill="#ddd")
    im.save(path)
    return path


def grid(rows, headers, path, cell=320, pad=12):
    """Сетка сравнения одной картинкой: столбцы с заголовками, над каждой строкой — подпись.

    rows — список (подпись, [пути к картинкам или None]); каждая картинка масштабируется
    к ширине cell, ячейки строки выравниваются по высоте, отсутствующая — прочерк.
    """
    n = len(headers)
    f_h, f_r = _font(22, bold=True), _font(19, bold=True)
    head = 46
    loaded = []
    for label, paths in rows:
        ims = []
        for p in paths:
            if p and os.path.exists(p):
                im = Image.open(p).convert("RGB")
                ims.append(im.resize((cell, round(im.height * cell / im.width)), Image.LANCZOS))
            else:
                ims.append(None)
        h = max((im.height for im in ims if im), default=cell // 2)
        loaded.append((label, ims, h))
    cap = 34
    W = n * cell + (n + 1) * pad
    H = head + sum(cap + h + pad for _, _, h in loaded) + pad
    out = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(out)
    for k, t in enumerate(headers):                                # заголовки столбцов
        x = pad + k * (cell + pad) + cell / 2
        d.text((x, head / 2), t, font=f_h, fill="black", anchor="mm")
    d.line([(pad, head - 2), (W - pad, head - 2)], fill=(150, 150, 150), width=2)
    y = head
    for label, ims, h in loaded:
        d.text((pad, y + cap / 2 + 2), label, font=f_r, fill=(40, 40, 40), anchor="lm")
        y += cap
        for k, im in enumerate(ims):
            x = pad + k * (cell + pad)
            if im:
                out.paste(im, (x, y + (h - im.height) // 2))
            else:
                d.text((x + cell / 2, y + h / 2), "—", font=f_h, fill=(120, 120, 120), anchor="mm")
        y += h + pad
        d.line([(pad, y - pad / 2), (W - pad, y - pad / 2)], fill=(220, 220, 220), width=1)
    out.save(path)
    return path


def lab12_grids(root):
    """Сетки «эталон | расчёт» для работ 1 и 2 (картинки уже построены блокнотами)."""
    labs = {"Lab1_diode_2D": [("Заряд и сетка", "z1_заряд"), ("Потенциал", "z1_потенциал"),
                              ("Заряд в сечении", "z1_разрез")],
            "Lab2_diode_2D_mesh": [("Заряд и сетка", "z2_заряд"), ("Потенциал", "z2_потенциал"),
                                   ("Заряд в сечении", "z2_разрез"), ("ВАХ на двух сетках", "z3_вах"),
                                   ("Потенциал, сравнение сеток", "z3_потенциал"),
                                   ("Без внешнего напряжения: заряд", "z4_заряд"),
                                   ("Без внешнего напряжения: сечение", "z4_разрез")]}
    for lab, items in labs.items():
        d = os.path.join(root, lab)
        grid([(t, [os.path.join(d, "reference", f + ".png"), os.path.join(d, "results", f + ".png")])
              for t, f in items], ["эталон", "расчёт"], os.path.join(d, "results", "сравнение.png"), cell=460)


if __name__ == "__main__":
    lab12_grids(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
