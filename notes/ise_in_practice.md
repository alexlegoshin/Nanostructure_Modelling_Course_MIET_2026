# Working with ISE TCAD: Mesh Refinement Rules, Reference-Matched Rendering and 3D Convergence

[Русский](#русский) · [English](#english) · [← к README](../README.md)

## Русский

### Работа с ISE TCAD

Особенности работы с ISE TCAD, выявленные в ходе лабораторных работ и не
связанные с запуском пакета (запуск описан в [отдельной заметке](ise_tcad_apple_silicon.md)).
Рассмотрены четыре вопроса: фактическое поведение генератора сетки, воспроизведение
эталонной визуализации из методических указаний, зависимость сходимости
трёхмерного расчёта от сетки и расчёт полевых транзисторов (работы 4–5).

#### Содержание

- [Сетка: генератор делит пополам, пока не влезет](#сетка-генератор-делит-пополам-пока-не-влезет)
- [Воспроизведение эталонной визуализации](#воспроизведение-эталонной-визуализации)
- [3D в ISE: решатель, сетка и ложные признаки успеха](#3d-в-ise-решатель-сетка-и-ложные-признаки-успеха)
- [MESFET в ISE: сетка, несходимость, смешанный режим](#mesfet-в-ise-сетка-несходимость-смешанный-режим)

---

### Сетка: генератор делит пополам, пока не влезет

`MaxElementSize` — не размер ячейки, а потолок. Генератор `mesh` режет область
пополам, пока ячейка не станет меньше потолка. Поэтому `Max = 0.2` на окне
шириной 2 мкм даёт не 0.2, а 0.125: 0.25 под 0.2 не проходит, значит, ещё одно
деление. Из-за этого первая сетка работы 1 получилась вдвое гуще эталонной, и ток
расходился с эталоном на 9%.

Правильные значения для варианта 2 (d = 0.8 мкм) определены по эталонным
иллюстрациям из файла вариантов подсчётом линий сетки:

| | Mesh1 Max | Mesh1 Min | Mesh2 Max | Mesh2 Min |
|---|---|---|---|---|
| работа 1 | (0.5 0.2) | (0.1 0.05) | (0.25 0.1) | (0.05 0.025) |
| работа 2 | (0.5 0.1) | (0.1 0.025) | (0.125 0.1) | (0.025 0.0125) |

Ещё две особенности, видимые только на эталонной иллюстрации:

- **Областей сгущения три, а не две.** Если считать линии отдельно внутри окна
  у анода и снаружи, верхняя половина прибора мельче нижней по всей ширине, а у
  анода ещё мельче. Двумя областями так не выйдет: либо верх грубый, либо низ
  лишний раз поделён. Третья область `Mesh3` на верхнюю половину решает задачу —
  128 узлов, поузловое совпадение с эталоном.
- **В работе 2 измельчаются не все направления.** По Ox краевые ячейки первой сетки
  остаются 0.5 мкм, а шаг второй сетки по Oy трогать нельзя — иначе у анода
  появляются лишние слои, отсутствующие в эталоне.

Итог: ток при 4 В — 0.00580 А против эталонных 0.00577 (работа 1) и 0.00548 против
0.00548 (работа 2).

**Край анода — особая точка.** Минимум заряда сидит ровно в x = −0.5, на краю
контакта, и при сгущении сетки не сходится: 108 узлов дают −1.14·10¹⁷,
139 — −2.03·10¹⁷, 349 — −2.38·10¹⁷. Привязывать к нему цветовую шкалу нельзя,
цвет будет меняться при любой правке сетки. В picasso для этого есть `model range`,
и мануал прямо советует ставить круглые границы.

### Воспроизведение эталонной визуализации

Визуализация реализована в [tools/ise_style.py](../tools/ise_style.py) и
откалибрована по измерениям: параметры сняты попиксельно с эталонных иллюстраций
(в формате `.doc` они хранятся как обычные PNG и извлекаются поиском сигнатуры).
Найденное позднее руководство picasso подтвердило почти все параметры.

- Палитра — ровно **31 уровень**, от (0, 42, 255) до (153, 0, 0). Это не
  градиент: внутри полосы цвет строго постоянный.
- Заряд — в шкале **ареасинуса**. Он меняет знак и меняется на полтора десятка
  порядков; на линейной шкале всё, кроме обеднённого слоя, схлопывается в один цвет.
- Потенциал — только линии уровня на белом, без заливки.
- Линия p-n перехода (153, 0, 0) — отдельный рисуемый объект (в picasso —
  `model sjunction 2.0 brown`), а не контур поля. Если принять её за данные,
  она нарушит калибровку шкалы. То же с контактами (`model scontact 2.0
  magenta`) и сеткой (`model sedge 1.0 black`).
- Графики: засечки наружу, моноширинный жирный шрифт, экспонента вида `-5e+016`.

В работе 3 ([tools/ise3d.py](../tools/ise3d.py),
[make_figures.py](../Lab3_diode_3D/make_figures.py)):

- 3D-иллюстрации — в ракурсе эталона: перспективная камера подогнана по силуэту
  прибора на эталонной картинке (`fit_camera`). Рёбра коробки — 2 пикселя,
  внутренняя сетка — 1.
- Ось Y графиков, как у inspect, — ровно по данным (у эталона 0…5.3 мА и
  37 716…488 235 А/см²), поэтому кривые всех решателей одной высоты.
- На эталонных продольных сечениях x = 0.75 и x = 0.25 нарисован не заряд, а lg|J|
  (проверено попиксельно), шкала — общая на весь прибор.
- Сечения ISE строятся из трёхмерного поля по тетраэдрам сетки: в срезах
  `dfisetools -cut` вектор тока только в плоскости среза, нормальная составляющая
  теряется. Линия `topline` идёт в координатах среза (u = −x).
- У самописного решателя ячейки прямоугольные, поэтому его структура нарисована
  «кирпичами».

**Определяющий фактор — место применения шкалы.** Команда picasso называется
`device interpol <набор> linear | log | arsinh`, и ключевое слово тут
*interpol*. Преобразуются значения в узлах, интерполяция внутри треугольника идёт
уже в преобразованных величинах, и только потом результат режется на полосы.
Если интерполировать по самому значению, а логарифм брать только для границ
полос, изображение получается заметно краснее: через толстую ячейку у катода большое
значение протягивается далеко вниз.

| доля площади каждого цвета, расхождение с эталоном | по значению | в преобразованных величинах |
|---|---|---|
| лаба 1, заряд | 22.6% | 12.0% |
| лаба 2, заряд | 18.6% | 13.5% |
| лаба 2, без смещения | 16.3% | 10.1% |

Параметр ареасинуса `ARSINH_A = 10^13.95` подобран по трём эталонам сразу.
Толщина линий сетки — 0.7. Метрика доли тёмных пикселей для неё ненадёжна
(сглаженные тонкие линии не проходят жёсткий порог), поэтому толщина выбрана
визуальным сравнением с эталоном.

### 3D в ISE: решатель, сетка и ложные признаки успеха

**Линейный решатель.** Командный файл работы 3 был составлен по шаблону работ 1–2,
где нет строки `method`. По умолчанию `dessis` берёт `Blocked`, а мануал прямо пишет,
для чего какой:

| решатель | для чего |
|---|---|
| `ParDiSo`, `Super` | один прибор, сетка до 10 000 узлов |
| `Slip` | один прибор, больше 8000 узлов |
| `Blocked` | задачи с несколькими приборами (смешанный режим) |

Без `method=slip` связанный расчёт выводил заголовок таблицы итераций и
завершался, не выполнив ни одной. С ним диод A сошёлся до 4 В. Пример из
методических указаний (`Sh3/sh2_des.cmd`) использует тот же `slip`.

**Сетка.** Первая сетка работы 3 получена из сетки примера (d = 2 мкм) делением
шагов по Oz на 2.5, по аналогии с работами 1–2, где вдоль толщины делится всё:

| | Mesh1 Max | Mesh1 Min | Mesh2 Max | Mesh2 Min | узлов |
|---|---|---|---|---|---|
| пример, d = 2 мкм | (0.25 0.25 0.25) | (0.05 0.05 0.05) | (0.1 0.1 0.1) | (0.01 0.01 0.01) | — |
| первая сетка | (0.25 0.25 0.1) | (0.05 0.05 0.02) | (0.1 0.1 0.04) | (0.02 0.02 0.01) | 5751 |
| сетка эталона | (0.25 0.25 0.2) | (0.05 0.05 0.02) | (0.2 0.2 0.1) | (0.02 0.02 0.01) | 1820 |

На первой сетке диод B не сошёлся ни при одной настройке: `slip`, `super`,
`pardiso`, `blocked`, пять схем управления шагом, дополнительное сгущение у края
анода, память виртуалки с 1 до 3 ГБ. При 3 ГБ расчёт доходил до 0.04–0.4 В, от
запуска к запуску по-разному, иногда расходясь в `1.#QNAN`.

Сетка эталона подобрана перебором параметров (около 30 с на вариант в XP).
Каждая сетка отрисовывалась в ракурсе эталонной иллюстрации (камера подогнана
по её силуэту, [tools/ise3d.py](../tools/ise3d.py), `fit_camera`), качество
оценивалось долей совпавших пикселей линий (F1) по каждой грани отдельно:

| | верх | передняя грань | переход | низ | торец | всего |
|---|---|---|---|---|---|---|
| первая сетка | | | | | | 0.874 |
| сетка эталона | 0.906 | 0.962 | 0.987 | 0.947 | 0.957 | 0.938 |

Ключевое отличие — шаги по Oz не делятся на 2.5: у анода 0.125 мкм по Ox и Oy
(у первой сетки 0.0625), по Oz около 0.1 мкм в объёме и до 0.025 у перехода. Остаток
расхождения — у анода: плотная полоса под ним у эталона уходит вниз до z ≈ 0.25, у
ISE — до z ≈ 0.56 (особенность генератора, параметрами не устраняется).

На сетке эталона оба диода сходятся до 4 В с командным файлом из примера без
изменений, по 9–10 минут, с 1 ГБ памяти. Ток при 3.95 В: A — 5.39 мА (эталон 5.30),
B — 3.30 мА (эталон 3.25), на 1.5–4 В расхождение не больше 2.8% и 4.1%. Почему на
первой сетке B не сходился, не установлено; отличия первой сетки — втрое больше
узлов и более плоские ячейки у анода.

**Сетка эталона по сетке не сошлась.** С той же физикой при сгущении сетки ток
меняется: при 1.5 В ток A — 3.09 мА у ISE (1820 узлов), 3.03 у DEVSIM (10 тыс.),
3.55 у самописного решателя (76 тыс.); при 3.95 В ток B — 3.30, 3.07 и 2.80 мА.
Грубая сетка смягчает излом ВАХ и завышает ток узкого анода: у края анода
контрольные объёмы контакта выходят за его границу на половину ячейки. То есть
эталон воспроизводится повторением его сетки, а не более точным решением
([разбор](devsim_3d.md#сравнение-с-эталоном-варианта-2)).

**Ненадёжные признаки успешного расчёта:**

- **коду возврата.** `dessis` запускает два процесса; нулевой код принадлежит
  пусковому, тогда как рабочий может быть уже завершён аварийно. Командный файл при этом всё равно
  выводит «ALL DONE». Проверять надо результат — сколько точек в `.plt`;
- **очереди `at`.** Старые задания оставались в очереди и перезапускали командный
  файл поверх идущего расчёта, перезаписывая результаты. Перед каждым запуском — `at /delete /yes`;
- **`taskkill` по дочерним процессам.** Сам командный файл при этом не
  останавливается, доходит до конца и создаёт видимость успешного прогона;
- **конфигу UTM при открытом UTM.** Память виртуалки в `config.plist` меняется
  только при закрытом приложении: иначе приложение использует загруженную копию
  конфигурации и запускает QEMU со старым значением. Проверять в госте:
  `systeminfo | findstr "Полный объем"`.

### MESFET в ISE: сетка, несходимость, смешанный режим

Работы 4 и 5 — полевые транзисторы Шоттки на GaAs.

**Командные файлы.** Командные файлы Sentaurus 2012 из примеров методических указаний
ISE 7.0 принимает без изменений: барьер Шоттки, AlGaAs с мольной долей 1, гетерограницы,
`Save`/`Load`, неполная ионизация (`Ion.par`), смешанный режим с цепью. Модели сужения
зоны и `Enormal` на GaAs в ISE 7.0 не действуют; смена движущей силы насыщения на
`Eparallel` нарушает расчёт.

**Сетка.** Решающим оказался тип сетки: её нужно строить, как в указаниях, командой
`mesh t` — прямоугольные ячейки с треугольниками на переходах. С ключом `-t` (только
треугольники):

- в работе 4 на структурах с h = 0.01 и h = 0 при Vd = 2 В были узкие диапазоны Vg, где
  метод Ньютона не сходился ни при каком шаге, а излом передаточной ВАХ выходил мягче
  эталонного — пики производных в задании 3 были в полтора раза ниже;
- в работе 5 семейство Id(Vg) обрывалось до максимума тока.

Такие диапазоны на треугольной сетке проходились «лесенкой» прыжков
(`lab4_files.des_transfer_jumps`): неудачный `Quasistationary` пропускается, и следующий
начинается за проблемным участком. В задании 3 работы 4 развёртка до сих пор идёт
участками с прыжком около Vg = −0.15 В.

**Несходимость на `mesh t`.** В работе 5 прямой проход Id(Vg) при Vd = 2 В
(Vg = −10 → 2 В) останавливается у Vg ≈ −6.7 В: шаг уменьшается до 10⁻¹⁵, итерации
колеблются без сходимости. Кривая посчитана от открытого канала, Vg = 0, вверх до 2 В
и вниз до −10 В (`lab5_files.des_open_channel`) и собрана из проходов; на общем
участке −9.2…−6.7 В ток обоих проходов — порядка 10⁻¹³ А/мм.

**Эталоны Svisual.** Подписи «Vd = 0.2 (V)» и «Vd = 0.8 (V)» в легенде эталонного
семейства Id(Vg) работы 5 — округление Svisual значений 0.25 и 0.75 В из примера
указаний (`t_family_2_des.cmd`). Проверка по самому эталону: его кривая «0.2» при
Vg = 0 даёт 0.206 А/мм, а эталонное семейство Id(Vd) при Vg = 0, Vd = 0.2 В — 0.17 А/мм;
0.206 соответствует Vd = 0.25 В. Кривая Vd = 1.5 В на эталоне не видна: по-видимому,
её расчёт оборвался, и точки лежат на нуле под кривой Vd = 2 В.

**Порог в работе 4.** Пик первой производной передаточной ВАХ (красный пунктир задания 3,
уменьшен вдвое) у ISE — 0.133, на эталоне он выходит за верх шкалы 0.15: излом ВАХ у ISE
положе не меньше чем на 12%. Параметры материалов ISE 7.0 проверены: в `GaAs.par` —
подвижность Arora (8500 см²/(В·с) без примесей), скорость насыщения 7.7·10⁶ см/с; в
`AlGaAs.par` при x = 1 — ширина зоны 2.11 эВ и сродство к электрону 3.56 эВ, как у AlAs.
Явных ошибок нет; расхождение остаётся в различиях физики ISE 7.0 и Sentaurus 2012
(библиотеки материалов, обработка гетерограниц). Подгонка параметров под эталон не
проводилась.

**Очередь расчётов.** Расчёты в XP идут через [tools/xp_queue.py](../tools/xp_queue.py):
задания ставятся через `at`, завершённые отмечаются в `queue.txt`. При нехватке места на
диске (менее ≈15 ГБ) служба macOS `cache_delete` завершает UTM вместе с виртуальной
машиной; очередь раз в 3 минуты проверяет XP, при остановке поднимает машину через
`utmctl` и повторяет прерванный расчёт с начала. Виртуальная машина одноядерная —
расчёты только последовательные: три параллельных прогона за ночь дошли лишь до 1.9 мс
переходного процесса из 4.

**Время расчёта** (M1, эмуляция XP):

| работа | сетка | узлов | время |
|---|---|---|---|
| 4 | `mesh t` | ≈1930 | задания 1 и 4 — 70 мин, каждая структура задания 2 — 15 мин, задание 3 — 35 мин |
| 5 | `mesh t` | 901 | ВАХ — 13–25 мин, переходный процесс 4 мс — около 2 часов |

---

## English

### Working with ISE TCAD

Peculiarities of ISE TCAD found during the labs that are not related to launching the package (launching is described in a [separate note](ise_tcad_apple_silicon.md#english)). Four questions are covered: how the mesh generator actually behaves, how the reference visualization from the lab manual was reproduced, how the convergence of the 3D computation depends on the mesh, and the field-effect transistor labs (4–5).

#### Contents

- [Mesh: the generator halves until it fits](#mesh-the-generator-halves-until-it-fits)
- [Reproducing the reference visualization](#reproducing-the-reference-visualization)
- [3D in ISE: solver, mesh and false signs of success](#3d-in-ise-solver-mesh-and-false-signs-of-success)
- [MESFET in ISE: mesh, non-convergence, mixed mode](#mesfet-in-ise-mesh-non-convergence-mixed-mode)

### Mesh: the generator halves until it fits

`MaxElementSize` is not the cell size but an upper bound. The `mesh` generator keeps halving the region until the cell is smaller than the bound. So `Max = 0.2` on a 2 µm wide window gives 0.125 rather than 0.2: 0.25 does not fit under 0.2, which means one more division. Because of this, the first mesh of lab 1 came out twice as dense as the reference one, and the current differed from the reference by 9%.

The correct values for variant 2 (d = 0.8 µm) were determined from the reference figures in the variants file by counting mesh lines:

| | Mesh1 Max | Mesh1 Min | Mesh2 Max | Mesh2 Min |
|---|---|---|---|---|
| lab 1 | (0.5 0.2) | (0.1 0.05) | (0.25 0.1) | (0.05 0.025) |
| lab 2 | (0.5 0.1) | (0.1 0.025) | (0.125 0.1) | (0.025 0.0125) |

Two more features are visible only in the reference figure:

- **There are three refinement regions, not two.** Counting the lines separately inside the window near the anode and outside it shows that the upper half of the device is finer than the lower half across the whole width, and finer still near the anode. Two regions cannot produce this: either the top stays coarse or the bottom gets divided once too often. A third region, `Mesh3`, over the upper half solves the problem: 128 nodes, node-for-node agreement with the reference.
- **In lab 2 not all directions are refined.** Along Ox the edge cells of the first mesh stay at 0.5 µm, and the Oy step of the second mesh must not be touched, otherwise extra layers appear near the anode that the reference does not have.

Result: the current at 4 V is 0.00580 A against the reference 0.00577 (lab 1) and 0.00548 against 0.00548 (lab 2).

**The anode edge is a singular point.** The charge minimum sits exactly at x = −0.5, on the contact edge, and does not converge with mesh refinement: 108 nodes give −1.14·10¹⁷, 139 give −2.03·10¹⁷, 349 give −2.38·10¹⁷. The colour scale must not be tied to it, otherwise the colours change with every mesh edit. picasso has `model range` for this, and the manual explicitly recommends round limits.

### Reproducing the reference visualization

The visualization is implemented in [tools/ise_style.py](../tools/ise_style.py) and calibrated by measurement: the parameters were taken pixel by pixel from the reference figures (in the `.doc` files they are stored as ordinary PNGs and extracted by searching for the signature). The picasso manual, found later, confirmed almost all of them.

- The palette has exactly **31 levels**, from (0, 42, 255) to (153, 0, 0). It is not a gradient: inside a band the colour is strictly constant.
- Charge is shown on an **arsinh** scale. It changes sign and spans some fifteen orders of magnitude; on a linear scale everything except the depletion layer collapses into one colour.
- Potential is shown as contour lines only, on white, with no fill.
- The p-n junction line (153, 0, 0) is a separate drawn object (in picasso, `model sjunction 2.0 brown`), not a contour of the field. If it is taken for data, it breaks the scale calibration. The same applies to the contacts (`model scontact 2.0 magenta`) and the mesh (`model sedge 1.0 black`).
- Plots: outward ticks, bold monospaced font, exponents of the form `-5e+016`.

In lab 3 ([tools/ise3d.py](../tools/ise3d.py), [make_figures.py](../Lab3_diode_3D/make_figures.py)):

- The 3D figures use the reference view: a perspective camera fitted to the device silhouette in the reference figure (`fit_camera`). Box edges are 2 pixels wide, the inner mesh 1 pixel.
- As in inspect, the Y axis of the plots spans exactly the data (0…5.3 mA and 37 716…488 235 A/cm² in the reference), so the curves of all solvers have the same height.
- The reference longitudinal sections x = 0.75 and x = 0.25 show lg|J|, not charge (checked pixel by pixel), with one scale for the whole device.
- The ISE sections are built from the 3D field on the mesh tetrahedra: in `dfisetools -cut` slices the current vector lies only in the slice plane, and the normal component is lost. The `topline` line runs in slice coordinates (u = −x).
- The own solver has rectangular cells, so its structure is drawn as "bricks".

**The decisive factor is where the scale is applied.** The picasso command is `device interpol <dataset> linear | log | arsinh`, and the key word is *interpol*. The nodal values are transformed, the interpolation inside a triangle is done on the transformed values, and only then is the result cut into bands. If the value itself is interpolated and the logarithm is applied only to the band limits, the image comes out noticeably redder: a large value is dragged far down through a thick cell near the cathode.

| difference from the reference in the area fraction of each colour | interpolating the value | interpolating the transformed value |
|---|---|---|
| lab 1, charge | 22.6% | 12.0% |
| lab 2, charge | 18.6% | 13.5% |
| lab 2, zero bias | 16.3% | 10.1% |

The arsinh parameter `ARSINH_A = 10^13.95` was fitted to three references at once. The mesh line width is 0.7. The dark-pixel fraction metric is unreliable for it (thin antialiased lines do not pass a hard threshold), so the width was chosen by visual comparison with the reference.

### 3D in ISE: solver, mesh and false signs of success

**Linear solver.** The lab 3 command file was written from the template of labs 1–2, which has no `method` line. By default `dessis` uses `Blocked`, and the manual states plainly what each solver is for:

| solver | intended for |
|---|---|
| `ParDiSo`, `Super` | one device, mesh up to 10 000 nodes |
| `Slip` | one device, more than 8000 nodes |
| `Blocked` | problems with several devices (mixed mode) |

Without `method=slip` the coupled computation printed the header of the iteration table and finished without doing a single iteration. With it, diode A converged up to 4 V. The example from the lab manual (`Sh3/sh2_des.cmd`) uses the same `slip`.

**Mesh.** The first lab 3 mesh was obtained from the example mesh (d = 2 µm) by dividing the Oz steps by 2.5, by analogy with labs 1–2, where everything along the thickness is divided:

| | Mesh1 Max | Mesh1 Min | Mesh2 Max | Mesh2 Min | nodes |
|---|---|---|---|---|---|
| example, d = 2 µm | (0.25 0.25 0.25) | (0.05 0.05 0.05) | (0.1 0.1 0.1) | (0.01 0.01 0.01) | — |
| first mesh | (0.25 0.25 0.1) | (0.05 0.05 0.02) | (0.1 0.1 0.04) | (0.02 0.02 0.01) | 5751 |
| reference mesh | (0.25 0.25 0.2) | (0.05 0.05 0.02) | (0.2 0.2 0.1) | (0.02 0.02 0.01) | 1820 |

On the first mesh diode B did not converge with any setting: `slip`, `super`, `pardiso`, `blocked`, five step control schemes, extra refinement at the anode edge, VM memory from 1 to 3 GB. With 3 GB the computation reached 0.04–0.4 V, differently from run to run, sometimes diverging to `1.#QNAN`.

The reference mesh was found by searching over the parameters (about 30 s per variant in XP). Each mesh was rendered in the view of the reference figure (camera fitted to its silhouette, [tools/ise3d.py](../tools/ise3d.py), `fit_camera`), and the quality was measured by the fraction of matching line pixels (F1) on each face separately:

| | top | front face | junction | bottom | end face | total |
|---|---|---|---|---|---|---|
| first mesh | | | | | | 0.874 |
| reference mesh | 0.906 | 0.962 | 0.987 | 0.947 | 0.957 | 0.938 |

The key difference is that the Oz steps are not divided by 2.5: near the anode the mesh is 0.125 µm along Ox and Oy (0.0625 in the first mesh), along Oz about 0.1 µm in the bulk and down to 0.025 at the junction. The remaining difference is near the anode: the dense band under it goes down to z ≈ 0.25 in the reference and to z ≈ 0.56 in ISE (a feature of the generator that the parameters do not remove).

On the reference mesh both diodes converge up to 4 V with the example command file unchanged, in 9–10 minutes each, with 1 GB of memory. The current at 3.95 V: A — 5.39 mA (reference 5.30), B — 3.30 mA (reference 3.25); at 1.5–4 V the difference is at most 2.8% and 4.1%. Why B did not converge on the first mesh has not been established; the first mesh has three times more nodes and flatter cells near the anode.

**The reference mesh is not mesh-converged.** With the same physics the current keeps changing as the mesh is refined: at 1.5 V current A is 3.09 mA in ISE (1820 nodes), 3.03 in DEVSIM (10 thousand) and 3.55 in the own solver (76 thousand); at 3.95 V current B is 3.30, 3.07 and 2.80 mA. A coarse mesh softens the IV knee and overestimates the current of the narrow anode: at the anode edge the contact control volumes extend half a cell beyond it. In other words, the reference is reproduced by repeating its mesh, not by a more accurate solution ([analysis](devsim_3d.md#comparison-with-the-variant-2-reference)).

**Unreliable signs of a successful run:**

- **the return code.** `dessis` starts two processes; the zero code belongs to the launcher, while the worker may already have crashed. The batch file still prints "ALL DONE". The result has to be checked: the number of points in the `.plt`;
- **the `at` queue.** Old jobs stayed in the queue and restarted the batch file on top of a running computation, overwriting the results. Before each run: `at /delete /yes`;
- **`taskkill` on child processes.** The batch file itself does not stop, runs to the end and gives the appearance of a successful run;
- **the UTM config while UTM is open.** The VM memory in `config.plist` changes only while the application is closed: otherwise the application uses its loaded copy of the configuration and starts QEMU with the old value. Check in the guest: `systeminfo | findstr "Полный объем"` (the Russian XP label for total physical memory).

### MESFET in ISE: mesh, non-convergence, mixed mode

Labs 4 and 5 are GaAs Schottky-gate field-effect transistors.

**Command files.** ISE 7.0 accepts the Sentaurus 2012 command files from the lab manual examples unchanged: Schottky barrier, AlGaAs with mole fraction 1, heterointerfaces, `Save`/`Load`, incomplete ionization (`Ion.par`), mixed mode with a circuit. The bandgap narrowing and `Enormal` models have no effect on GaAs in ISE 7.0; switching the saturation driving force to `Eparallel` breaks the computation.

**Mesh.** The mesh type turned out to be decisive: it has to be built as in the manual, with `mesh t` — rectangular cells with triangles at the transitions. With the `-t` switch (triangles only):

- in lab 4, on the structures with h = 0.01 and h = 0 at Vd = 2 V, there were narrow Vg ranges where Newton did not converge with any step, and the knee of the transfer characteristic came out softer than in the reference — the derivative peaks in task 3 were one and a half times lower;
- in lab 5 the Id(Vg) family stopped before the current maximum.

On the triangular mesh such ranges were passed with a "ladder" of jumps (`lab4_files.des_transfer_jumps`): a failed `Quasistationary` is skipped, and the next one starts beyond the problematic interval. In lab 4, task 3, the sweep still runs in segments with a jump around Vg = −0.15 V.

**Non-convergence on `mesh t`.** In lab 5 the forward Id(Vg) sweep at Vd = 2 V (Vg = −10 → 2 V) stops at Vg ≈ −6.7 V: the step shrinks to 10⁻¹⁵ and the iterations oscillate without converging. The curve was computed from the open channel, Vg = 0, up to 2 V and down to −10 V (`lab5_files.des_open_channel`) and assembled from the sweeps; on the common interval −9.2…−6.7 V the current of both sweeps is of order 10⁻¹³ A/mm.

**Svisual references.** The labels "Vd = 0.2 (V)" and "Vd = 0.8 (V)" in the legend of the reference Id(Vg) family of lab 5 are Svisual's rounding of the values 0.25 and 0.75 V from the manual example (`t_family_2_des.cmd`). A check on the reference itself: its "0.2" curve gives 0.206 A/mm at Vg = 0, while the reference Id(Vd) family gives 0.17 A/mm at Vg = 0, Vd = 0.2 V; 0.206 corresponds to Vd = 0.25 V. The Vd = 1.5 V curve is not visible in the reference: apparently its computation stopped, and its points lie at zero under the Vd = 2 V curve.

**Threshold in lab 4.** The peak of the first derivative of the transfer characteristic (the red dashed line of task 3, halved) is 0.133 in ISE, while in the reference it goes above the top of the 0.15 scale: the ISE knee is at least 12% less steep. The ISE 7.0 material parameters were checked: `GaAs.par` has Arora mobility (8500 cm²/(V·s) undoped) and a saturation velocity of 7.7·10⁶ cm/s; `AlGaAs.par` at x = 1 gives a bandgap of 2.11 eV and an electron affinity of 3.56 eV, as for AlAs. There are no obvious errors; the difference lies in the physics of ISE 7.0 versus Sentaurus 2012 (material libraries, treatment of heterointerfaces). The parameters were not fitted to the reference.

**Job queue.** The computations in XP run through [tools/xp_queue.py](../tools/xp_queue.py): jobs are scheduled with `at`, and finished ones are marked in `queue.txt`. When the disk runs low (below ≈15 GB free), the macOS `cache_delete` service terminates UTM together with the virtual machine; the queue checks XP every 3 minutes, restarts the machine with `utmctl` when it stops and repeats the interrupted computation from the start. The virtual machine has one core, so the computations can only run sequentially: three parallel runs overnight reached only 1.9 ms of the 4 ms transient.

**Run times** (M1, XP emulation):

| lab | mesh | nodes | time |
|---|---|---|---|
| 4 | `mesh t` | ≈1930 | tasks 1 and 4 — 70 min, each task 2 structure — 15 min, task 3 — 35 min |
| 5 | `mesh t` | 901 | IV — 13–25 min, 4 ms transient — about 2 hours |
