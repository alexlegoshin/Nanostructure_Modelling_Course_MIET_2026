# -*- coding: utf-8 -*-
"""Сводный лист: эталон и наша картинка парами, с подписями."""

import os
from PIL import Image, ImageDraw, ImageFont


def _font(size):
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc"):
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
