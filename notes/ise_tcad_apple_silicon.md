# ISE TCAD 7.0 на Apple Silicon

[Русский](#русский) · [English](#english) · [← к README](../README.md)

## Русский

### Как запустить пакет 2001 года на MacBook Air M1

Задача звучала просто: сделать лабораторные по моделированию полупроводниковых
приборов. Подвох в том, что они идут на TCAD-пакете старше большинства
студентов курса, собранном под Windows NT и Intel, — а под рукой ARM-макбук.
Ниже — как это прошло и все грабли по дороге. Всё проверено запуском, а не
догадками.

### Что это за пакет

ISE TCAD 7.0 выпускала Integrated Systems Engineering AG из Цюриха. В 2004 году
компанию купил Synopsys, и продукт стал Sentaurus TCAD — тем самым, что стоит
в половине микроэлектронных лабораторий мира.

Родство видно невооружённым глазом: решатель до сих пор называется DESSIS,
формат данных — DF-ISE, а в современных мануалах Sentaurus иногда проскакивают
старые имена программ. Пакет 2001 года — прямой предок нынешнего.

Что нужно для работы:

| программа | назначение | интерфейс |
|---|---|---|
| `mesh` | сетка по описанию геометрии | консоль |
| `dessis` | решает уравнения Пуассона и непрерывности | консоль |
| `dfisetools` | разрезы, распределения вдоль линии | консоль |
| `mdraw` | графический редактор структуры | X11 |
| `inspect` | графики: ВАХ, разрезы, осциллограммы | X11 |
| `picasso`, `tecplot_ise` | 2D- и 3D-карты полей | X11 |

Одна деталь важнее всех остальных: **ISE 7.0 под Windows — это юниксовый
пакет, портированный через Cygwin.** Отсюда и X-сервер в комплекте, и
большая часть странностей ниже.

### Стенд

```
MacBook Air M1 (ARM64)
  └─ UTM 4.7.5, полная эмуляция x86
       └─ QEMU, цель i386
            └─ Windows XP SP3
                 ├─ ISE TCAD 7.0 (порт через Cygwin)
                 ├─ X-сервер Labtam X-WinPro
                 └─ встроенный Telnet-сервер
```

Самописный telnet-клиент на Python ([tools/xp.py](../tools/xp.py)) заходит с мака
в гостевую систему; через него запускаются расчёты и забираются результаты.
Всем управляет Jupyter.

Виртуальный диск — около шести гигабайт, гостю хватает одного гигабайта ОЗУ
(для 3D-задач больше — см. [лабу 3](../README.md#лабораторная-3-3d-диод)).

### Грабля первая: XP не ставится

Установка Windows намертво висела на первом же экране — *«Setup is inspecting
your computer's hardware configuration»*.

Смотрим, как UTM запускает QEMU:

```
-machine pc,vmport=off,i8042=off,hpet=off
```

`i8042=off` отключает контроллер клавиатуры PS/2. Современным системам он не
нужен — хватает USB HID, — поэтому UTM выключает его по умолчанию. Но
NTDETECT в Windows XP при старте ищет именно контроллер 8042 и без него
зависает навсегда.

Это известная проблема UTM, [#3723](https://github.com/utmapp/UTM/issues/3723).
Лечится включением PS/2 в настройках виртуалки; в конфиге это ключ
`PS2Controller`. После этого флаг пропадает из командной строки, и установка
идёт нормально.

Полезный побочный эффект: без контроллера PS/2 не работала бы и клавиатура
в текстовом режиме установки, а там нужны Enter и F8.

### Управление из терминала

Кликать по эмулированному рабочему столу быстро надоедает; цель была
запускать расчёты скриптами. В XP Professional для этого есть встроенный
Telnet Server — ставить ничего не надо:

```
sc config tlntsvr start= auto
net start tlntsvr
tlntadmn config sec=-NTLM +passwd
```

Третья строка обязательна. По умолчанию сервер требует NTLM-аутентификацию,
которую юниксовые клиенты не умеют, и вход молча не проходит.

В брандмауэре XP нужно открыть порт:

```
netsh firewall set portopening TCP 23 Telnet ENABLE
```

**Системный telnet с мака не работает.** Он подключается и молчит. Дамп
трафика показал, что сервер честно шлёт согласование опций и ждёт ответа:

```
FF FB 01   IAC WILL ECHO
FF FB 03   IAC WILL SUPPRESS-GO-AHEAD
FF FD 27   IAC DO NEW-ENVIRON
FF FD 1F   IAC DO NAWS
FF FD 00   IAC DO BINARY
```

Клиент и сервер так и не договариваются. Решение — свой маленький клиент:
принимать только ECHO и SGA, представляться терминалом VT100, остальное
вежливо отклонять.

Вторая важная деталь: **следующая команда отправляется только после
появления приглашения `>`**, а не по таймеру. Иначе команда попадает в
середину идущего расчёта. `dessis` считает минутами, и без синхронизации по
приглашению всё разваливается.

Третья: вывод приходит в cp866 с ANSI-последовательностями позиционирования
курсора, их надо вычищать. Помогает перевод сервера в потоковый режим:

```
tlntadmn config mode=stream
```

**Долгие расчёты — через планировщик.** Windows убивает всё дерево процессов
вместе с telnet-сессией; ни `start /b`, ни `start` с отдельной консолью не
спасают. Работает планировщик заданий:

```
at HH:MM C:\tcad\LAB3\runAll.bat
```

Задачу запускает служба `Schedule`, от telnet-сессии она не зависит. Три
ранних «падения» сложных задач (трек иона на 0.94 нс, транзиент на 5-м шаге,
развёртка на 85 пс) оказались одним и тем же: расчёт просто не доживал до
конца вместе с сессией.

### Грабля вторая: пробел в пути убивает программу

Счётная часть заработала сразу. А графические программы вели себя странно:
окно вспыхивало на секунду и пропадало. Ни ошибки, ни лога.

Перехват вывода всё объяснил:

```
ls: C:\Documents: No such file or directory
ls: and: No such file or directory
ls: Settings\User\Desktop: No such file or directory
```

Вот оно. `picasso` — юниксовая программа, и внутри она вызывает `ls` на
текущую папку **без кавычек вокруг пути**. Путь вида
`C:\Documents and Settings\...\Desktop\` разваливается по пробелам, программа
не может прочитать рабочую папку и молча выходит.

**Держите проекты в пути без пробелов и без кириллицы** — `C:\tcad\`
работает. Консольным `mesh`, `dessis` и `dfisetools` это не страшно: они
получают имена файлов аргументами.

### Грабля третья: окна, запущенные по telnet, не появляются

Следующая странность: программа работает, видна в списке процессов, честно
жжёт процессор — а окна нигде нет.

Причина в устройстве Windows: процесс, запущенный из telnet-сессии, попадает в
отдельную оконную станцию, и его окна на интерактивном рабочем столе не
рисуются.

Была разумная надежда, что X11 это обойдёт — клиент говорит с X-сервером по
TCP, окно создаёт сервер, а он живёт в консольной сессии. **Гипотеза проверена
и не подтвердилась**: окно всё равно не появляется.

Рабочее разделение в итоге такое:

- **по telnet** — всё счётное, оно и так консольное;
- **из консоли самой Windows** — графические программы, через меню «Пуск».

X-сервер должен быть запущен первым, иначе клиентам не к чему подключаться.

### picasso и X-сервер: что удалось и что нет

Хотелось получать картинки родной программой, а не подражанием. Вот что вышло.

**X-сервер (Labtam X-WinPro) поднимается, picasso на нём рисует.** Две грабли:

- запускать `xserver.exe` **из его собственной папки**
  ([tools/guest/startx.bat](../tools/guest/startx.bat)), иначе он ищет конфиг в
  `system32`, не находит и виснет на модальном окне «FontPath is completely
  invalid» — порт 6000 при этом не слушается;
- пути к шрифтам в `XWINPRO.ini` не должны содержать пробелов: короткие имена
  `PROGRA~1` не работают, генерация имён 8.3 на томе отключена. Поэтому шрифты
  скопированы в `C:\xfonts`, конфиг смотрит туда
  ([tools/guest/XWINPRO.ini](../tools/guest/XWINPRO.ini)).

**Чего не вышло:** сохранить картинку из picasso скриптом. `picasso -batch`
работает — TCL 8.2 исполняется, прибор грузится, команды проходят, — но запись
PostScript роняет программу. `page save`, `window save`, `page dump`
отчитываются успехом и не пишут файл. Поэтому третья панель в блокнотах
(«вывод самого picasso») ручная. Как получить её руками:

1. Поднять X-сервер (см. выше).
2. Запустить picasso из консоли XP:

   ```
   set DISPLAY=127.0.0.1:0
   cd /d C:\tcad\LAB1
   C:\ISE\bin\picasso sh1_msh.grd sh1_des.dat
   ```

3. В панели Model выбрать набор `SpaceCharge`, включить `rainbow`, в Draw style
   оставить `face`, `edge`, `contact`, `junction`. Шкалу —
   Device → interpol → arsinh.
4. Снять окно и положить PNG в папку `picasso/` в корне репозитория с именем как у
   эталона (`z1_заряд.png` и т. п.) — блокнот подхватит её третьей панелью.

Те же команды в виде TCL — [tools/guest/init.pic](../tools/guest/init.pic):
picasso сам подхватывает `init.pic` из текущей папки.

Из мануала picasso при этом подтвердилось многое из того, что было снято с
эталона по пикселям: линия перехода, контакты и сетка — отдельные рисуемые
объекты (`model sjunction 2.0 brown`, `model scontact 2.0 magenta`,
`model sedge 1.0 black`), а цветовой диапазон задаётся `model range` — ниже
минимума всё синее, выше максимума всё красное.

### Чтение результатов: формат DF-ISE

ISE пишет результаты в собственном текстовом формате. Раз это текст, разумно
разбирать его на Python и рисовать на маке современными средствами
([tools/dfise.py](../tools/dfise.py)). У формата две неочевидные особенности.

**Элементы заданы рёбрами, а не вершинами.** Ожидаешь, что треугольник — это
три вершины. На деле это три ребра, а рёбра ссылаются на вершины:

```
Vertices (1957) { 0 0   0 0.2625   0.625 0.2625  ... }
Edges (3994)    { 0 1   1 2   2 3   3 0  ... }
Elements (2071) { 3 0 1 2 3    1 3 0    3 4 5 6 -2  ... }
```

Первое число элемента — его тип: 0 точка, 1 отрезок, 2 треугольник,
3 четырёхугольник, 5 тетраэдр (в 3D он задан уже гранями). Остальное — индексы
рёбер, и **отрицательный индекс значит, что ребро пройдено в обратную
сторону**. Чтобы получить кольцо вершин, рёбра надо обойти и сшить. В 3D
поверхность прибора берётся из блока `Locations`: метки `i`/`e` отмечают
внутренние и внешние грани.

**Поля могут храниться кусками.** У простого прибора поле — один массив на всю
сетку. У структуры из нескольких регионов — по блоку на регион:

```
Dataset ("ElectrostaticPotential") {
  validity = [ "S10" ]
  Values (428) { ... }
}
```

В транзисторе из четырнадцати регионов каждое поле разбито на одиннадцать
таких блоков, их надо сшивать: значения внутри блока идут по возрастанию
глобальных номеров вершин этого региона.

**Контакты тоже лежат в сетке** — обычными регионами из отрезков с материалом
`Contact`. Геометрию контактов надёжнее брать оттуда, а не из `.bnd`: при
смене варианта иначе всё разъедется.

### Отрисовка

Родной визуализатор рисует поля дискретными цветовыми полосами от синего
через зелёный к красному, с тонким чёрным контуром прибора. Одна условность
непривычна: **ось Y направлена вниз** — сечения приборов рисуют так, чтобы
верхний электрод был сверху.

Повторить это в Plotly ([tools/viz.py](../tools/viz.py)) или matplotlib
([tools/ise_style.py](../tools/ise_style.py)) несложно. Тонкость в том, что сетка
неструктурированная: поле сначала нужно интерполировать на регулярную сетку и
обрезать по исходной триангуляции — иначе заливка вылезет за границу прибора.

Не задавайте осям одинаковый масштаб: для транзистора длиной пятнадцать
микрон и глубиной два это растянет картинку в море пустоты. Лучше вычислять
высоту рисунка из пропорций прибора.

### Сколько это считается

Замеры на одном эмулированном ядре M1:

| задача | узлов | время |
|---|---|---|
| 2D диод, сетка | 162 | 0.5 с |
| 2D диод, развёртка до 4 В | 162 | 33 с |
| 2D транзистор, две развёртки | 1994 | 16 мин |
| 3D диод, развёртка до 4 В | 4711 | 24 мин |
| транзистор в схеме, транзиент 4 мс | 802 | ~35 мин |

Вывод неожиданный: **опасения, что эмуляция будет слишком медленной, не
подтвердились.** Двумерные задачи считаются за секунды. Узкие места — 3D и
транзиенты, но и они укладываются в полчаса: медленно, чтобы раздражать,
но достаточно быстро, чтобы работать.

### Что в итоге

Полностью рабочая цепочка: расчёт запускается из Jupyter одним вызовом,
результаты сами забираются на мак, графики строятся современными средствами.
Сам пакет 2001 года оставлен в точности как был — внутри ничего не
патчилось и не менялось.

Обобщения, которые полезны и за пределами этого пакета:

1. **Старым системам нужны старые контроллеры.** Отключение PS/2 ради
   современности ломает всё, что старше Windows Vista.
2. **Юниксовые программы под Windows ненавидят пробелы в путях** — особенно
   когда внутри вызывают консольные утилиты.
3. **GUI нельзя запустить по telnet.** Разделяйте счётную и графическую части
   работы.
4. **Синхронизируйтесь по приглашению, а не по таймеру.** Это единственный
   надёжный способ управлять долгими задачами через сетевой шелл.
5. **Текстовые форматы — подарок.** Пока данные текстовые, их всегда можно
   прочитать своими средствами, даже когда родной визуализатор отказывается
   запускаться.

Последний пункт оказался самым ценным: свой парсер снял всякую зависимость от
того, работает ли графика внутри виртуалки вообще.

### Что написано по дороге

- [xp.py](../tools/xp.py) — telnet-клиент: согласование опций, синхронизация по приглашению,
  перекодировка; заодно забирает файлы из гостевой системы
- [put.py](../tools/put.py) — заливает текстовые файлы внутрь построчно, без общих папок
- [dfise.py](../tools/dfise.py) — разбор DF-ISE: сетка, элементы через рёбра, поля по регионам
- [viz.py](../tools/viz.py), [ise_style.py](../tools/ise_style.py) — отрисовка в стиле родного визуализатора
- блокноты Jupyter — по одному на лабу

---

## English

### Running a 2001 semiconductor package on a MacBook Air M1

The task sounded simple: complete a set of coursework labs on semiconductor device modelling. The catch was that they run on a TCAD package older than most of the students taking the course, built for Windows NT and Intel hardware — while the machine at hand was an ARM MacBook.

Here is how it went, and every rake stepped on along the way. Everything below was verified by actually running it, not by guessing.

------------------------------------------------------------------------

### What the package is

ISE TCAD 7.0 came from Integrated Systems Engineering AG in Zurich. Synopsys acquired the company in 2004, and the product became Sentaurus TCAD — the tool sitting in half the microelectronics labs in the world today.

The lineage is visible without squinting: the solver is still called DESSIS, the data format is still DF-ISE, and modern Sentaurus manuals occasionally slip and use the old program names. The 2001 package is a direct ancestor of the current one.

The parts needed for the work:

| Program | Purpose | Interface |
|----|----|----|
| `mesh` | mesh generation from a geometry description | console |
| `dessis` | solves Poisson and continuity equations | console |
| `dfisetools` | cutlines, distributions along a line | console |
| `mdraw` | graphical structure editor | X11 |
| `inspect` | plots: I-V curves, cutlines, waveforms | X11 |
| `picasso`, `tecplot_ise` | 2D and 3D field maps | X11 |

One detail matters more than any other: **ISE 7.0 for Windows is Unix software ported through Cygwin.** That explains the bundled X server, and it explains most of the behaviour described below.

------------------------------------------------------------------------

### The setup

```
MacBook Air M1 (ARM64)
  └─ UTM 4.7.5, full x86 emulation
       └─ QEMU, i386 target
            └─ Windows XP SP3
                 ├─ ISE TCAD 7.0 (Cygwin port)
                 ├─ Labtam X-WinPro X server
                 └─ built-in Telnet Server
```

A hand-written Python telnet client connects from the Mac into the guest; simulations are launched and results retrieved through it. Everything is driven from Jupyter.

The virtual disk sits at about six gigabytes, and one gigabyte of RAM is plenty for the guest.

------------------------------------------------------------------------

### Rake one: XP will not install

Windows setup hung dead on the very first screen — *"Setup is inspecting your computer's hardware configuration."*

Looking at how UTM invokes QEMU:

```
-machine pc,vmport=off,i8042=off,hpet=off
```

`i8042=off` disables the PS/2 keyboard controller. Modern operating systems do not need it — USB HID is enough — so UTM turns it off by default. But Windows XP's NTDETECT probes for exactly that 8042 controller at startup, and without it it stalls forever.

This is [a known UTM issue, \#3723](https://github.com/utmapp/UTM/issues/3723). The fix is re-enabling PS/2 in the VM settings; in the config file it is the `PS2Controller` key. Once set, the flag disappears from the launch line and setup proceeds normally.

A useful side effect: without a PS/2 controller the keyboard would not work in text-mode setup either, and that stage needs Enter and F8.

------------------------------------------------------------------------

### Driving it from a terminal

Clicking through an emulated Windows desktop gets old fast; the goal was to script the runs. XP Professional ships a Telnet Server for exactly this — nothing to install:

```
sc config tlntsvr start= auto
net start tlntsvr
tlntadmn config sec=-NTLM +passwd
```

That third line is not optional. By default the server demands NTLM authentication, which Unix clients do not speak, and logins fail with no useful message.

The XP firewall also needs the port opened:

```
netsh firewall set portopening TCP 23 Telnet ENABLE
```

#### The system telnet client did not work

The macOS client simply goes quiet with this server: it connects and prints nothing at all. Dumping the raw traffic showed the server dutifully sending option negotiation and waiting for an answer:

```
FF FB 01   IAC WILL ECHO
FF FB 03   IAC WILL SUPPRESS-GO-AHEAD
FF FD 27   IAC DO NEW-ENVIRON
FF FD 1F   IAC DO NAWS
FF FD 00   IAC DO BINARY
```

Client and server never agreed. The fix was a small custom client: accept only ECHO and SGA, advertise a VT100 terminal, politely decline everything else.

The second important detail: **the next command is sent only after the `>` prompt appears**, never on a timer. Otherwise a command lands in the middle of a running simulation. `dessis` takes minutes, and without prompt synchronisation the whole thing falls apart.

Third: output arrives in cp866 with ANSI cursor-positioning escapes that must be stripped. Switching the server to stream mode helps:

```
tlntadmn config mode=stream
```

------------------------------------------------------------------------

### Rake two: a space in the path kills the program

The computational side worked immediately. The graphical tools, however, behaved strangely: a window would flash up for a second and vanish. No error, no log.

Capturing the output revealed it:

```
ls: C:\Documents: No such file or directory
ls: and: No such file or directory
ls: Settings\User\Desktop: No such file or directory
```

There it is. `picasso` is Unix software, and internally it shells out to `ls` on the current directory **without quoting the path**. A path like `C:\Documents and Settings\...\Desktop\` splits on the spaces, the program cannot read its working directory, and it exits silently.

**Keep projects in a path with no spaces and no non-ASCII characters** — `C:\tcad\` works fine. The console tools `mesh`, `dessis` and `dfisetools` are immune, since they receive filenames as arguments.

------------------------------------------------------------------------

### Rake three: windows launched over telnet never appear

The next oddity: the program is running, visible in the process list, happily burning CPU — and there is no window anywhere on screen.

The cause is how Windows works: a process started from a telnet session lands in a separate window station, and its windows are never drawn on the interactive desktop.

There was a reasonable hope that X11 would sidestep this — the client talks to the X server over TCP, and the window is created by the server, which lives in the console session. **The hypothesis was tested and did not hold**: the window still does not appear.

The working split ended up being:

- **over telnet** — everything computational, which is console-only anyway;
- **from the Windows console itself** — the graphical tools, via the Start menu.

The X server has to be started first, or the clients have nothing to connect to.

------------------------------------------------------------------------

### Reading the results: the DF-ISE format

ISE writes results in its own text-based format. Since it is text, the sensible move is to parse it in Python and plot on the Mac with modern tooling. The format has two non-obvious quirks.

#### Elements are defined by edges, not vertices

You would expect a triangle to be described by three vertices. In fact it is three edges, and the edges reference the vertices:

```
Vertices (1957) { 0 0   0 0.2625   0.625 0.2625  ... }
Edges (3994)    { 0 1   1 2   2 3   3 0  ... }
Elements (2071) { 3 0 1 2 3    1 3 0    3 4 5 6 -2  ... }
```

The first number of an element is its type: 1 for a segment, 2 for a triangle, 3 for a quadrilateral. The rest are edge indices, and **a negative index means the edge is traversed backwards**. To recover a vertex ring you have to walk the edges and stitch them together.

#### Fields may be stored in pieces

For a simple device a field is one array covering the whole mesh. For a structure with several regions it is one block per region:

```
Dataset ("ElectrostaticPotential") {
  validity = [ "S10" ]
  Values (428) { ... }
}
```

In a fourteen-region transistor each field is split across eleven such blocks, and they have to be merged: values inside a block follow ascending global vertex indices of that region.

------------------------------------------------------------------------

### Plotting

The package's native visualiser draws fields as discrete colour bands running blue through green to red, with a thin black device outline. One convention is unusual: **the Y axis points downward** — device cross-sections are drawn that way so the top electrode appears on top.

Reproducing this in Plotly is straightforward. The subtlety is that the mesh is unstructured, so the field must first be interpolated onto a regular grid and masked against the original triangulation — otherwise the fill spills outside the device boundary.

Do not force an equal aspect ratio on the axes: for a transistor fifteen microns long and two microns deep that stretches the figure across a sea of blank space. Compute the figure height from the device's aspect ratio instead.

------------------------------------------------------------------------

### How fast it actually runs

Measurements on a single emulated core of an M1:

| Task                                    | Nodes | Time    |
|-----------------------------------------|-------|---------|
| 2D diode, mesh generation               | 162   | 0.5 s   |
| 2D diode, ramp to 4 V                   | 162   | 33 s    |
| 2D transistor, two ramps                | 1994  | 16 min  |
| 3D diode, ramp to 4 V                   | 4711  | 24 min  |
| Transistor in a circuit, 4 ms transient | 802   | ~35 min |

The conclusion was unexpected: **worries about emulation being too slow did not materialise.** Two-dimensional problems finish in seconds. The bottlenecks are 3D and transient analysis, and even those stay under half an hour — slow enough to be annoying, fast enough to work with.

------------------------------------------------------------------------

### What came out of it

A fully working chain: simulations launch from Jupyter with a single call, results are pulled back to the Mac automatically, and plots are produced with modern tooling. The 2001 package itself is left exactly as it was — nothing was patched or modified inside it.

Generalisations worth carrying beyond this particular package:

1. **Old operating systems need old controllers.** Disabling PS/2 in the name of modernity breaks anything older than Windows Vista.
2. **Unix software on Windows hates spaces in paths** — especially when it shells out to command-line utilities internally.
3. **GUIs cannot be launched over telnet.** Split the console and graphical halves of the workflow.
4. **Synchronise on the prompt, not on a timer.** It is the only reliable way to drive long-running jobs through a network shell.
5. **Text formats are a gift.** As long as the data is text you can always read it with your own tools, even when the native visualiser refuses to start.

That last point turned out to be the most valuable one: a custom parser removed any dependency on whether the graphics worked inside the virtual machine at all.

------------------------------------------------------------------------

### Tooling written along the way

- `xp.py` — telnet client with option negotiation, prompt synchronisation and transcoding; also retrieves files from the guest
- `put.py` — uploads text files into the guest line by line, no shared folders required
- `dfise.py` — DF-ISE parser: mesh, edge-defined elements, per-region fields
- `viz.py` — Plotly rendering in the style of the original package
- five Jupyter notebooks, one per lab assignment
