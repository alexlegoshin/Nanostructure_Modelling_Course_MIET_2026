#!/usr/bin/env python3
"""Выполнить команды в Windows XP (ISE TCAD) через встроенный telnet-сервер.

    python3 tools/xp.py "hostname" "echo %ISEROOT%"
    python3 tools/xp.py -f script.txt      # по команде на строку

Адрес и учётка гостевой XP берутся из переменных окружения:
    export XP_HOST=192.168.64.2 XP_USER=user XP_PASSWORD=...

Свой клиент вместо системного telnet: macOS-овский с этим сервером
не договаривается по опциям и молчит. Здесь минимальное согласование
(ECHO/SGA принимаем, остальное отклоняем, TTYPE=VT100) плюс чистка
ANSI и перекодировка cp866.
"""
import socket, sys, time, re

import os

HOST = os.environ.get("XP_HOST", "192.168.64.2")   # адрес UTM в режиме Shared Network
USER = os.environ.get("XP_USER", "")
PASSWORD = os.environ.get("XP_PASSWORD", "")
IAC, DONT, DO, WONT, WILL, SB, SE = 255, 254, 253, 252, 251, 250, 240
ECHO, SGA, TTYPE = 1, 3, 24
ANSI = re.compile(rb"\x1b\[[0-9;]*[A-Za-z]")


def _negotiate(sock, data, out):
    i = 0
    reply = b""
    while i < len(data):
        b = data[i]
        if b == IAC and i + 1 < len(data):
            cmd = data[i + 1]
            if cmd in (DO, DONT, WILL, WONT) and i + 2 < len(data):
                opt = data[i + 2]
                if cmd == DO:
                    reply += bytes([IAC, WILL if opt == TTYPE else WONT, opt])
                elif cmd == WILL:
                    reply += bytes([IAC, DO if opt in (ECHO, SGA) else DONT, opt])
                i += 3
                continue
            if cmd == SB:
                j = data.find(bytes([IAC, SE]), i)
                if j < 0:
                    break
                if data[i + 2:j] and data[i + 2] == TTYPE:
                    reply += bytes([IAC, SB, TTYPE, 0]) + b"VT100" + bytes([IAC, SE])
                i = j + 2
                continue
            i += 2
            continue
        out.append(b)
        i += 1
    if reply:
        sock.sendall(reply)


def run(commands, wait=1.0, total=900, idle_limit=25):
    """Логинится и выполняет команды. Возвращает вывод сессии текстом.

    Следующая строка уходит только когда сервер показал приглашение
    (`>` для cmd, `login:`/`password:` при входе), иначе долгие команды
    вроде dessis обрывались бы досрочно.
    """
    queue = [USER.encode("cp866") + b"\r\n", PASSWORD.encode("cp866") + b"\r\n"]
    queue += [c.encode("cp866") + b"\r\n" for c in commands]
    queue.append(b"exit\r\n")

    sock = socket.create_connection((HOST, 23), timeout=15)
    sock.settimeout(wait)
    buf = bytearray()
    try:
        start = time.time()
        idle = 0.0
        sent_at = 0
        while time.time() - start < total:
            try:
                data = sock.recv(8192)
            except socket.timeout:
                idle += wait
                if idle >= idle_limit:
                    break
                continue
            if not data:
                break
            idle = 0.0
            _negotiate(sock, data, buf)
            tail = ANSI.sub(b"", bytes(buf[-400:])).decode("cp866", errors="replace")
            tail = tail.rstrip()
            ready = tail.endswith(">") or tail.endswith("login:") or tail.endswith("password:")
            if ready and queue and len(buf) != sent_at:
                time.sleep(0.3)
                sock.sendall(queue.pop(0))
                sent_at = len(buf)
    finally:
        # Закрывать обязательно даже при прерывании ячейки: у telnet-сервера XP
        # ограничено число одновременных сессий, и брошенные соединения его съедают.
        try:
            sock.close()
        except Exception:
            pass

    text = ANSI.sub(b"", bytes(buf)).decode("cp866", errors="replace")
    if "предела подключений" in text or "connection limit" in text.lower():
        raise RuntimeError(
            "telnet-сервер отказал: исчерпан лимит одновременных сессий.\n"
            "Обычно это брошенные соединения от прерванных ячеек.\n"
            "Лечится перезапуском ядра Jupyter либо командой в виртуалке: tlntadmn -k all")
    return "\n".join(line.rstrip() for line in text.splitlines())


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["-f"]:
        cmds = [l.strip() for l in open(args[1], encoding="utf-8") if l.strip()]
    else:
        cmds = args
    print(run(cmds))


def fetch(remote, local, tries=3):
    """Забрать файл из Windows. Телнет иногда роняет в поток кусок своей
    служебной строки — поэтому после выгрузки файл проверяется на мусор
    и при необходимости тянется заново."""
    JUNK = ("---FILE-", "echo ", "exit", "C:\\Documents")
    for attempt in range(tries):
        _fetch_once(remote, local)
        txt = open(local, encoding="utf-8", errors="replace").read()
        if not any(j in line for line in txt.splitlines()[:-1] for j in JUNK):
            return local
    raise IOError("не удалось выгрузить %s без мусора за %d попыток" % (remote, tries))


def _fetch_once(remote, local):
    """Забрать текстовый файл из Windows на мак.

    Файлы DF-ISE — обычный текст, поэтому достаточно вывести их командой
    `type` и поймать вывод между маркерами. Для двоичных файлов не годится.
    """
    # Всё одной командой: если слать тремя, эхо следующей может влезть
    # в середину вывода при ложном срабатывании детектора приглашения.
    out = run(["echo ---FILE-BEGIN---& type " + remote + "& echo ---FILE-END---"],
              total=1800, idle_limit=300)
    try:
        body = out.rsplit("---FILE-BEGIN---", 1)[1].split("---FILE-END---", 1)[0]
    except IndexError:
        raise RuntimeError("не удалось прочитать " + remote)
    lines = [l for l in body.splitlines()
             if not l.lstrip().startswith(("C:\\", "echo ", "type "))]
    while lines and not lines[0].strip():
        lines.pop(0)
    text = "\n".join(lines).rstrip() + "\n"
    if local:
        open(local, "w", encoding="utf-8", newline="\n").write(text)
    return text
