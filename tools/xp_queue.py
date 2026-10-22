#!/usr/bin/env python3
"""Очередь расчётов в XP, которая переживает падения виртуальной машины.

    python3 tools/xp_queue.py C:\\tcad\\L4q task4 task2_h000            # папки с t.bnd, t.cmd, t_des.cmd
    python3 tools/xp_queue.py C:\\tcad\\L5 task3:t_circuit_des.cmd     # другой командный файл решателя

В каждой папке: `mesh t` (если сетки ещё нет) и `dessis`. Готовые отмечаются в
<папка>\\queue.txt. Раз в 3 минуты проверяется, отвечает ли XP; если виртуальная машина
остановилась (такое бывает без видимой причины), она запускается через utmctl, и
недосчитанное ставится в очередь заново — начатый расчёт повторяется с начала.
"""
import os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xp, put

UTMCTL = "/Applications/UTM.app/Contents/MacOS/utmctl"
VM = "Win XP"


def alive():
    try:
        xp.run(["ver"], total=30)
        return True
    except Exception:
        return False


def ensure_vm():
    if alive():
        return False
    st = subprocess.run([UTMCTL, "status", VM], capture_output=True, text=True).stdout
    if "started" not in st:
        print(time.strftime("%H:%M"), "виртуальная машина остановлена — запускаю", flush=True)
        subprocess.run([UTMCTL, "start", VM])
    for _ in range(40):
        time.sleep(15)
        if alive():
            return True
    raise SystemExit("XP не поднялась")


def done(work):
    try:
        out = xp.run([r"type %s\queue.txt" % work])
    except Exception:
        return set()
    return set(re.findall(r"^DONE (\S+)", out, re.M))


def queue(work, runs):
    lines = ["@echo off"]
    for r in runs:
        d, des = (r.split(":") + ["t_des.cmd"])[:2]
        lines += [r"cd /d %s\%s" % (work, d), r"if not exist t_msh.grd C:\ISE\bin\mesh t > m.log 2>&1",
                  r"C:\ISE\bin\dessis %s > run.log 2>&1" % des, r"echo DONE %s >> %s\queue.txt" % (r, work)]
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "queue.bat")
    with open(path, "w", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")
    xp.run(put.commands_for(path, work + r"\queue.bat"), total=600)
    os.remove(path)
    now = xp.run(["time /t"]).split("time /t")[-1]
    h, m = map(int, re.search(r"\b(\d{1,2}):(\d{2})\b", now).groups())
    m += 1; h = (h + m // 60) % 24; m %= 60
    xp.run(["at /delete /yes", r"at %02d:%02d cmd /c %s\queue.bat" % (h, m, work)])
    print(time.strftime("%H:%M"), "в очереди:", ", ".join(runs), flush=True)


def main():
    work, runs = sys.argv[1], sys.argv[2:]
    ensure_vm()
    queue(work, [r for r in runs if r not in done(work)])
    while True:
        time.sleep(180)
        if ensure_vm():                              # машину подняли — расчёт прерван
            left = [r for r in runs if r not in done(work)]
            if left:
                queue(work, left)
        left = [r for r in runs if r not in done(work)]
        if not left:
            print(time.strftime("%H:%M"), "всё готово", flush=True)
            return


if __name__ == "__main__":
    main()
