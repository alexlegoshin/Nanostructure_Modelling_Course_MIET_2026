#!/usr/bin/env python3
"""Залить текстовый файл в Windows XP через telnet-шелл.

    python3 tools/put.py локальный_файл "C:\\lab\\Sh1\\sh1.bnd"

Файлы лаб — текст по паре килобайт, так что проще передать их
построчно через echo, чем гасить виртуалку ради монтирования
обменного диска.

Тонкость: перенаправление ставится ПЕРЕД echo (`>>файл echo текст`).
В обратном порядке cmd принял бы цифру перед `>` за номер потока —
строка вида `echo Value = 1e+017>>файл` молча ушла бы не туда.
"""
import sys, xp

SPECIAL = "^&<>|()"


def escape(line):
    out = line.replace("^", "^^")
    for ch in "&<>|()":
        out = out.replace(ch, "^" + ch)
    return out


def commands_for(local, remote, batch=8):
    """Команды заливки файла. Строки пакуются по batch штук в одну команду:
    `>>файл (echo a& echo b& ...)`. Одна строка на команду работает, но для
    файлов в тысячу строк это тысяча сетевых обменов и десяток минут."""
    text = open(local, encoding="utf-8", errors="replace").read()
    parts = ["echo." if l.strip() == "" else "echo " + escape(l)
             for l in text.splitlines()]
    cmds = ["type nul > " + remote]
    for i in range(0, len(parts), batch):
        chunk = "& ".join(parts[i:i + batch])
        cmds.append(">>%s (%s)" % (remote, chunk))
    return cmds


if __name__ == "__main__":
    local, remote = sys.argv[1], sys.argv[2]
    cmds = commands_for(local, remote)
    print("строк: %d" % (len(cmds) - 1))
    print(xp.run(cmds)[-400:])
