# Validating DEVSIM Against ISE in 3D: Control-Volume Error, ISE Physics Port and Comparison with the Reference

[Русский](#русский) · [English](#english) · [← к README](../README.md)

## Русский

### Проверка DEVSIM по ISE в 3D

На первой сетке ISE диод B работы 3 не сходился (в итоге оба диода рассчитаны в ISE
на сетке эталона — см. [заметку об ISE на практике](ise_in_practice.md#3d-в-ise-решатель-сетка-и-ложные-признаки-успеха)).
Поэтому задача была решена также в [DEVSIM](https://devsim.org) — открытом решателе
на Python, основанном на методе конечных объёмов; он же используется для проверки
сходимости по сетке. Для обоснования результатов потребовалось
устранить ошибку в самом DEVSIM, перенести физические модели из командного файла
ISE и проверить решение на задаче, для которой результат ISE известен.

#### Содержание

- [Завышение объёмов ячеек в DEVSIM](#завышение-объёмов-ячеек-в-devsim)
- [Физические модели из командного файла ISE](#физические-модели-из-командного-файла-ise)
- [Сетка ISE и проверка сходимости](#сетка-ise-и-проверка-сходимости)
- [Сравнение с эталоном варианта 2](#сравнение-с-эталоном-варианта-2)
- [Первый подход: сетка Gmsh](#первый-подход-сетка-gmsh)
- [Визуализация результатов DEVSIM](#визуализация-результатов-devsim)
- [Численная часть](#численная-часть)
- [Файлы и запуск](#файлы-и-запуск)

---

### Завышение объёмов ячеек в DEVSIM

В методе конечных объёмов поток по ребру умножается на площадь грани ячейки
Вороного, через которую он идёт (`EdgeCouple`). На тетраэдре кусок этой грани —
четырёхугольник: середина ребра, центры описанных окружностей двух прилегающих
граней и центр описанной сферы. Если центр сферы лежит вне тетраэдра, часть
вкладов отрицательна, и именно они гасят лишнее у соседей.

DEVSIM 2.11 в 3D складывает эти вклады **по модулю**, и суммарный объём ячеек
превышает объём прибора:

| сетка | сумма объёмов ячеек | геометрия |
|---|---|---|
| ISE, диод A | 3.06 мкм³ | 2.4 мкм³ |
| Gmsh, 8.6 тыс. узлов | 4.54–4.60 мкм³ | 2.4 мкм³ |
| Gmsh, 15.5 тыс. узлов | 4.00 мкм³ | 2.4 мкм³ |

Проводимость рёбер завышена так же, и ток выходит выше настоящего: на сетке ISE
на 10–15%, на сетке Gmsh — почти вдвое. Ошибка найдена в расчётах на ПК и
перепроверена на маке на тех же сетках (`NodeVolume` в сумме).

Площади пересчитываются со знаком отдельно ([tools/voronoi3d.py](../tools/voronoi3d.py)) и
подставляются множителями: все рёберные потоки — на `CR` = правильная площадь /
`EdgeCouple`, узловые заряды — на `VR` = правильный объём / `NodeVolume`. Со
знаками сумма A·L/3 по рёбрам тетраэдра равна его объёму в точности; объём
прибора — ровно 2.4. Режим `clip` дополнительно обрезает отрицательные площади
в ноль; на сетке ISE это то же самое (отрицательные там — шум ~10⁻¹⁷ мкм²).

Ошибка отправлена разработчикам как [devsim/devsim#171](https://github.com/devsim/devsim/issues/171).
Автор DEVSIM указал, что она известна (метод предполагает центры описанных сфер внутри
тетраэдров) и что встроенные модели площадей и объёмов заменяются через параметры
(`edge_couple_model`, `node_volume_model`, `element_edge_couple_model` и другие). Такой
путь чище множителей; он пока не опробован.

Исследование по сеткам —
[experiments/mesh_quality/](../experiments/mesh_quality/): объём и площади
контактов, отрицательные `EdgeCouple` на сетках не-Делоне, сравнение со знаком
против DEVSIM.

### Физические модели из командного файла ISE

Первоначально использовались модели самописного решателя (Коги — Томас, SRH).
Они давали 9.8–21 мА вместо 5.2 — отчасти из-за ячеек, отчасти из-за отличий в
физических моделях.
`sA_des.cmd` включает `Mobility(DopingDep HighFieldsat Enormal)` и
`BandGapNarrowing(OldSlotboom)`, рекомбинации нет. В
[tools/dev_ise.py](../tools/dev_ise.py) это перенесено так:

- подвижность по легированию — модель Масетти;
- насыщение скорости — Канали: v<sub>sat</sub> = 1.07·10⁷ / 8.37·10⁶ см/с,
  β = 1.109 / 1.213 для электронов / дырок;
- сужение запрещённой зоны — Слотбум (OldSlotboom);
- рекомбинации нет, как у ISE.

**Насыщение у ISE 7 — по модулю поля на элементе**, а не по градиенту квазиуровня
Ферми, как в новых Sentaurus, и не по проекции поля на ребро. ISE пишет в
`sA_des.dat` подвижности `eMobility`/`hMobility` в узлах: обращение формулы Канали по
ним даёт движущую силу, медиана отношения которой к |E| — ровно 1.00 для обоих
носителей, при слабом поле подвижность совпадает с Масетти до 1–3%
([experiments/ise_physics/](../experiments/ise_physics/)). Поэтому в DEVSIM поле
собирается на каждом тетраэдре из его рёбер, подвижность считается на элементе, а
поток Шарфеттера — Гуммеля берётся элементной моделью (`HFS_DRIVE = "elem"`, по
умолчанию). Варианты на сетке эталона:

| движущая сила | ток при 3.95 В, A / B | против ISE |
|---|---|---|
| градиент квазиуровня | — | излом ВАХ вдвое выше, наклон при малых токах n = 1.03 |
| проекция поля на ребро | 5.58 / 3.44 мА | +3.4% / +4.2% |
| **\|E\| на тетраэдре** | **5.34 / 3.29 мА** | **−1.0% / −0.4%** |

В собственных точках ВАХ ISE (DEVSIM с шагом 0.025 В) расхождение на 0.4–4 В —
от −3.4% до −1.0% (A) и от −3.4% до −0.4% (B). Прежний «провал на изломе» (−15% при
1 В) был артефактом логарифмической интерполяции по редким точкам обеих ВАХ.

**n<sub>i</sub> = 1.4385·10¹⁰ см⁻³** — откалибровано по ВАХ ISE при 0.1–0.5 В: там
ток пропорционален n<sub>i</sub>², и отношение к ISE постоянно.

`Enormal` — модель Ломбарди для границы полупроводника с диэлектриком. Диэлектрика
в приборе нет, так что у ISE она ни на что не влияет, и здесь не сделана.

### Сетка ISE и проверка сходимости

Тетраэдры, контакты и легирование в узлах читаются прямо из `sA_msh.grd` /
`sA_msh.dat` ([tools/ise_grid.py](../tools/ise_grid.py)). Анод диода B — правая
половина анода A на той же сетке: линия x = 0.5 у неё — линия узлов, ни один
треугольник анода её не пересекает, так что анод вырезается точно. У
преподавателя командные файлы сетки A и B одинаковы, так что это та же постановка.

Сходимость проверена тензорными сетками на осях сетки эталона
([tools/tensor_mesh.py](../tools/tensor_mesh.py)): каждый параллелепипед режется
на 6 тетраэдров Куна с общей диагональю, грани ячеек — точные прямоугольники,
площади неотрицательны. Деление каждого отрезка осей на N даёт 10 тыс. узлов при
N = 1, 76 тыс. при N = 2. На тех же сетках независимо считает самописный решатель
([tools/dd3d_ise.py](../tools/dd3d_ise.py)) — см. README, работа 3.

Совпадение DEVSIM с ISE на одной и той же сетке:

| сетка | узлов | 1.5–4 В | 0.3–1 В |
|---|---|---|---|
| первая | 5751 | −3.5…−0.9% (диод A) | 0.05% |
| эталона | 1820 | −1.9…−0.4% (A и B) | −3.4…−1.3% |

На сетке эталона отрицательных граней ячеек нет (`--box signed` и `clip` дают
одно и то же), так что остаток расхождения относится к дискретизации.

### Сравнение с эталоном варианта 2

Эталонные иллюстрации варианта 2 построены в Sentaurus TCAD 2012 — пакете, под
который написаны методические указания. Толщина прибора на них — 0.8 мкм, как в
варианте: профиль заряда на эталонном сечении совпадает с расчётом при 0.8 мкм.

Ток, мА:

| U, В | эталон A | ISE A, сетка эталона | DEVSIM A, 10 тыс. узлов | эталон B | ISE B, сетка эталона | DEVSIM B, 10 тыс. узлов |
|---|---|---|---|---|---|---|
| 1.5 | 3.01 | 3.09 | 3.03 | 2.03 | 2.11 | 2.00 |
| 2.0 | 4.14 | 4.21 | 4.11 | 2.68 | 2.74 | 2.57 |
| 3.0 | 5.03 | 5.10 | 4.96 | 3.11 | 3.16 | 2.94 |
| 3.95 | 5.30 | 5.39 | 5.24 | 3.25 | 3.30 | 3.07 |

ISE на сетке эталона воспроизводит эталон в пределах 1.4–4%. При сгущении сетки
ток меняется дальше: на 76 тыс. узлов (самописный решатель на GPU, та же физика) ток A
при 1.5 В — 3.55 мА (эталон 3.01), ток B при 3.95 В — 2.80 мА (эталон 3.25). Грубая
сетка эталона смягчает излом ВАХ и завышает ток узкого анода: контрольные объёмы
контакта выходят за край анода на половину ячейки. Прежние оценки (+31% и −11%)
завышены неточной моделью насыщения (по проекции поля на ребро), но вывод тот же:
эталон воспроизводится повторением его сетки, а не более точным расчётом.

Эталон оцифрован с `reference/z2_вах.png` по пикселям
([devsim/reference_iv.py](../Lab3_diode_3D/devsim/reference_iv.py)); ниже 1.5 В,
где кривая наиболее крутая, точность оцифровки ниже.

### Первый подход: сетка Gmsh

Первоначально расчёт выполнялся на сетке [Gmsh](https://gmsh.info) со сгущением к
переходу и кромкам анода: переход и анод встроены в геометрию как поверхности,
ступенька легирования и край контакта ложатся точно на узлы
([tools/mesh3d.py](../tools/mesh3d.py), [tools/dev3d.py](../tools/dev3d.py),
[devsim/run.py](../Lab3_diode_3D/devsim/run.py)). Подвижность — как в самописном
решателе, с насыщением по полю вдоль ребра или по полному |E| на тетраэдре
(элементная модель, 3D-аналог `mos_physics.py`).

| диод A, ток при 4 В | 8.6 тыс. узлов | 15.5 тыс. узлов |
|---|---|---|
| постоянная подвижность | 21.5 мА | — |
| насыщение по проекции на ребро | 12.1 мА | 11.4 мА |
| насыщение по \|E\| на тетраэдре | 10.4 мА | 9.8 мА |

Все значения завышены из-за ошибки в объёмах ячеек (4.0–4.6 мкм³ вместо 2.4) и
приведены для полноты. Корректный расчёт выполняет `run_ise.py`, в том числе на
сетке Gmsh (`--gmsh 2.5`) с поправкой.

### Визуализация результатов DEVSIM

[tools/py3d_plots.py](../tools/py3d_plots.py), сводный лист собирает
[make_figures.py](../Lab3_diode_3D/make_figures.py).

- **Срезы** интерполируются по настоящим тетраэдрам сетки (барицентрически), а не
  по триангуляции, построенной заново по облаку узлов: у той тетраэдры-щепки тянут значения через
  ступеньку легирования, и на срезе выходят ложные полосы. Интерполяция — в шкале
  ареасинуса, как у picasso.
- **Плотность тока на грани** — из тока узлов в той же дискретизации, что решал
  DEVSIM: поток по ребру × площадь грани ячейки (с поправкой `CR`). Сумма по
  узлам анода совпадает с током контакта до шестого знака, внутри прибора баланс
  нулевой — это и есть проверка. Поузловое «ток / площадь» на неструктурированной
  сетке шумит на десятки процентов, поэтому берётся сглаженное отношение
  Σ I·w / Σ A·w с окном 0.04 мкм — ток при этом не теряется.
- Более простые способы непригодны: разность полей у грани даёт ответ, зависящий от
  глубины второй точки в разы, а вектор J, собранный на тетраэдре из шести потоков
  по рёбрам, даёт ток через горизонтальные сечения от 5.4 до 11.5 мА при токе
  контакта 9.8.

### Численная часть

- **Прямой решатель обязателен.** Итерационный GMRES под смещением сообщает о
  сходимости на неправильном решении.
- **float128.** Ток Шарфеттера — Гуммеля — разность больших потоков, концентрации
  гуляют от 10³ до 10¹⁷ см⁻³. В double Ньютон застревает на 10⁻⁵, а ток при 0.1 В
  выходит миллиамперами. С `extended_model` + `extended_equation` сходимость
  квадратичная до 10⁻¹¹. Нужно только на малых токах — выше 0.7 В хватает double
  (`--fast`).
- **Память.** На первой сетке ISE (5.8 тыс. узлов) — 1.3 ГБ, 45 с на диод на M1
  (`--fast`); на сетке эталона (1.8 тыс.) — 0.6 ГБ, 150 с с float128 и 10 с с `--fast`. На сетке
  Gmsh UMFPACK на 34 тыс. узлов занимает около 2.6 ГБ; мелкие сетки считались на
  ПК — [заметка про рабочую станцию](workstation_fx8320_titanx.md).
- **Воспроизводимость.** ВАХ с мака (M1, OpenBLAS) и с ПК (FX-8320, MKL) совпали
  до 10⁻¹⁵.

### Файлы и запуск

| | |
|---|---|
| [tools/dev_ise.py](../tools/dev_ise.py) | физика ISE, поправка ячеек, развёртка |
| [tools/ise_grid.py](../tools/ise_grid.py) | сетка ISE целиком: тетраэдры по граням, контакты, легирование |
| [tools/voronoi3d.py](../tools/voronoi3d.py) | площади граней ячеек со знаком |
| [tools/tensor_mesh.py](../tools/tensor_mesh.py) | тензорные сетки на осях ISE |
| [tools/dev3d.py](../tools/dev3d.py), [tools/mesh3d.py](../tools/mesh3d.py) | первый подход: сетка Gmsh, подвижность по ребру и по \|E\| |
| [devsim/run_ise.py](../Lab3_diode_3D/devsim/run_ise.py) | основной расчёт |
| [devsim/plot_ise.py](../Lab3_diode_3D/devsim/plot_ise.py) | картинка верификации и таблицы |
| [devsim/reference_iv.py](../Lab3_diode_3D/devsim/reference_iv.py) | оцифровка эталонной ВАХ |

```bash
cd Lab3_diode_3D/devsim
python run_ise.py A --fast          # сетка ISE; сравнение с ise/sA_des.plt
python run_ise.py B --fast          # B на сетке A
python run_ise.py A --tensor 1      # проверка сходимости по сетке
python plot_ise.py                  # картинка верификации
cd .. && python make_figures.py     # сводный лист results/devsim_ise/
```

---

## English

### Validating DEVSIM against ISE in 3D

On the first ISE mesh, diode B of lab 3 did not converge (in the end both diodes were computed in ISE on the reference mesh — see the [note on ISE in practice](ise_in_practice.md#3d-in-ise-solver-mesh-and-false-signs-of-success)). The problem was therefore also solved in [DEVSIM](https://devsim.org), an open-source finite-volume device simulator with a Python interface; it is also used to check mesh convergence. Supporting the results required fixing an error in DEVSIM itself, porting the physical models from the ISE command file and checking the solution on a problem for which the ISE result is known.

#### Contents

- [Control volumes overestimated in DEVSIM](#control-volumes-overestimated-in-devsim)
- [Physical models from the ISE command file](#physical-models-from-the-ise-command-file)
- [ISE mesh and convergence check](#ise-mesh-and-convergence-check)
- [Comparison with the variant 2 reference](#comparison-with-the-variant-2-reference)
- [First approach: Gmsh mesh](#first-approach-gmsh-mesh)
- [Visualizing DEVSIM results](#visualizing-devsim-results)
- [Numerics](#numerics)
- [Files and running](#files-and-running)

### Control volumes overestimated in DEVSIM

In the finite volume method the flux along an edge is multiplied by the area of the Voronoi cell face it crosses (`EdgeCouple`). In a tetrahedron the piece of this face is a quadrilateral: the edge midpoint, the circumcenters of the two adjacent faces and the circumcenter of the tetrahedron. If the circumcenter lies outside the tetrahedron, part of the contributions are negative, and it is exactly these that cancel the excess added by the neighbours.

DEVSIM 2.11 adds these contributions **in absolute value** in 3D, and the total cell volume exceeds the device volume:

| mesh | sum of cell volumes | geometry |
|---|---|---|
| ISE, diode A | 3.06 µm³ | 2.4 µm³ |
| Gmsh, 8.6 thousand nodes | 4.54–4.60 µm³ | 2.4 µm³ |
| Gmsh, 15.5 thousand nodes | 4.00 µm³ | 2.4 µm³ |

The edge conductances are overestimated by the same factor, and the current comes out higher than the true one: by 10–15% on the ISE mesh and almost twofold on the Gmsh mesh. The error was found in the PC runs and re-checked on the Mac on the same meshes (sum of `NodeVolume`).

The areas are recomputed with sign separately ([tools/voronoi3d.py](../tools/voronoi3d.py)) and applied as multipliers: all edge fluxes are multiplied by `CR` = correct area / `EdgeCouple`, and the nodal charges by `VR` = correct volume / `NodeVolume`. With signs, the sum of A·L/3 over the edges of a tetrahedron equals its volume exactly, and the device volume is exactly 2.4. The `clip` mode additionally clips negative areas to zero; on the ISE mesh this makes no difference (the negative values there are noise of ~10⁻¹⁷ µm²).

The problem was reported as [devsim/devsim#171](https://github.com/devsim/devsim/issues/171). The DEVSIM author pointed out that it is known (the method assumes that circumcenters lie inside the tetrahedra) and that the built-in area and volume models can be replaced through parameters (`edge_couple_model`, `node_volume_model`, `element_edge_couple_model` and others). That route would be cleaner than the multipliers; it has not been tried yet.

A study across meshes is in [experiments/mesh_quality/](../experiments/mesh_quality/): volume and contact areas, negative `EdgeCouple` on non-Delaunay meshes, signed values against DEVSIM.

### Physical models from the ISE command file

Initially the models of the own solver were used (Caughey–Thomas, SRH). They gave 9.8–21 mA instead of 5.2, partly because of the cells and partly because of the differences in the physical models. `sA_des.cmd` enables `Mobility(DopingDep HighFieldsat Enormal)` and `BandGapNarrowing(OldSlotboom)`, with no recombination. In [tools/dev_ise.py](../tools/dev_ise.py) this is ported as follows:

- doping-dependent mobility: the Masetti model;
- velocity saturation: Canali, v<sub>sat</sub> = 1.07·10⁷ / 8.37·10⁶ cm/s, β = 1.109 / 1.213 for electrons / holes;
- bandgap narrowing: Slotboom (OldSlotboom);
- no recombination, as in ISE.

**In ISE 7 saturation is driven by |E| on the element**, not by the quasi-Fermi level gradient as in newer Sentaurus versions, and not by the projection of the field onto the edge. ISE writes the nodal mobilities `eMobility`/`hMobility` to `sA_des.dat`: inverting the Canali formula on them gives the driving force, whose median ratio to |E| is exactly 1.00 for both carriers, and at low field the mobility matches Masetti to 1–3% ([experiments/ise_physics/](../experiments/ise_physics/)). So in DEVSIM the field is assembled on each tetrahedron from its edges, the mobility is computed on the element, and the Scharfetter–Gummel flux is taken as an element model (`HFS_DRIVE = "elem"`, the default). Variants on the reference mesh:

| driving force | current at 3.95 V, A / B | against ISE |
|---|---|---|
| quasi-Fermi level gradient | — | IV knee twice as high, slope n = 1.03 at low currents |
| field projection onto the edge | 5.58 / 3.44 mA | +3.4% / +4.2% |
| **\|E\| on the tetrahedron** | **5.34 / 3.29 mA** | **−1.0% / −0.4%** |

At the points of the ISE IV itself (DEVSIM with a 0.025 V step) the discrepancy at 0.4–4 V ranges from −3.4% to −1.0% (A) and from −3.4% to −0.4% (B). The earlier "dip at the knee" (−15% at 1 V) was an artifact of logarithmic interpolation between the sparse points of both IVs.

**n<sub>i</sub> = 1.4385·10¹⁰ cm⁻³**, calibrated on the ISE IV at 0.1–0.5 V: there the current is proportional to n<sub>i</sub>², and the ratio to ISE is constant.

`Enormal` is the Lombardi model for a semiconductor–insulator interface. There is no insulator in the device, so in ISE it has no effect, and it is not implemented here.

### ISE mesh and convergence check

Tetrahedra, contacts and nodal doping are read directly from `sA_msh.grd` / `sA_msh.dat` ([tools/ise_grid.py](../tools/ise_grid.py)). The anode of diode B is the right half of anode A on the same mesh: the line x = 0.5 is a line of nodes there, and no anode triangle crosses it, so the anode is cut out exactly. The instructor's mesh command files for A and B are identical, so this is the same setup.

Mesh convergence was checked with tensor meshes on the axes of the reference mesh ([tools/tensor_mesh.py](../tools/tensor_mesh.py)): each box is split into 6 Kuhn tetrahedra sharing a diagonal, the cell faces are exact rectangles, and all areas are non-negative. Dividing each axis segment into N parts gives 10 thousand nodes for N = 1 and 76 thousand for N = 2. The own solver ([tools/dd3d_ise.py](../tools/dd3d_ise.py)) runs independently on the same meshes — see README, lab 3.

Agreement of DEVSIM with ISE on the same mesh:

| mesh | nodes | 1.5–4 V | 0.3–1 V |
|---|---|---|---|
| first | 5751 | −3.5…−0.9% (diode A) | 0.05% |
| reference | 1820 | −1.9…−0.4% (A and B) | −3.4…−1.3% |

The reference mesh has no negative cell faces (`--box signed` and `clip` give the same result), so the remaining discrepancy is due to the discretization.

### Comparison with the variant 2 reference

The variant 2 reference figures were made in Sentaurus TCAD 2012, the package the lab manual is written for. The device thickness on them is 0.8 µm, as in the variant: the charge profile on the reference cross-section matches the computation at 0.8 µm.

Current, mA:

| U, V | reference A | ISE A, reference mesh | DEVSIM A, 10 thousand nodes | reference B | ISE B, reference mesh | DEVSIM B, 10 thousand nodes |
|---|---|---|---|---|---|---|
| 1.5 | 3.01 | 3.09 | 3.03 | 2.03 | 2.11 | 2.00 |
| 2.0 | 4.14 | 4.21 | 4.11 | 2.68 | 2.74 | 2.57 |
| 3.0 | 5.03 | 5.10 | 4.96 | 3.11 | 3.16 | 2.94 |
| 3.95 | 5.30 | 5.39 | 5.24 | 3.25 | 3.30 | 3.07 |

ISE on the reference mesh reproduces the reference within 1.4–4%. With mesh refinement the current keeps changing: on 76 thousand nodes (own GPU solver, same physics) current A at 1.5 V is 3.55 mA (reference 3.01), and current B at 3.95 V is 2.80 mA (reference 3.25). The coarse reference mesh softens the IV knee and overestimates the current of the narrow anode: the contact control volumes extend half a cell beyond the anode edge. The earlier estimates (+31% and −11%) were inflated by an inaccurate saturation model (field projection onto the edge), but the conclusion stands: the reference is reproduced by repeating its mesh, not by a more accurate computation.

The reference IV was digitized from `reference/z2_вах.png` pixel by pixel ([devsim/reference_iv.py](../Lab3_diode_3D/devsim/reference_iv.py)); below 1.5 V, where the curve is steepest, the digitization is less accurate.

### First approach: Gmsh mesh

Initially the computation was done on a [Gmsh](https://gmsh.info) mesh refined towards the junction and the anode edges: the junction and the anode are embedded in the geometry as surfaces, so the doping step and the contact edge fall exactly on nodes ([tools/mesh3d.py](../tools/mesh3d.py), [tools/dev3d.py](../tools/dev3d.py), [devsim/run.py](../Lab3_diode_3D/devsim/run.py)). The mobility is that of the own solver, with saturation driven either by the field along the edge or by the full |E| on the tetrahedron (an element model, the 3D analogue of `mos_physics.py`).

| diode A, current at 4 V | 8.6 thousand nodes | 15.5 thousand nodes |
|---|---|---|
| constant mobility | 21.5 mA | — |
| saturation by the projection onto the edge | 12.1 mA | 11.4 mA |
| saturation by \|E\| on the tetrahedron | 10.4 mA | 9.8 mA |

All these values are inflated by the cell volume error (4.0–4.6 µm³ instead of 2.4) and are given for completeness. The correct computation is `run_ise.py`, including on the Gmsh mesh (`--gmsh 2.5`) with the correction.

### Visualizing DEVSIM results

[tools/py3d_plots.py](../tools/py3d_plots.py); the summary sheet is assembled by [make_figures.py](../Lab3_diode_3D/make_figures.py).

- **Slices** are interpolated on the actual mesh tetrahedra (barycentrically), not on a triangulation rebuilt from the node cloud: the sliver tetrahedra of the latter drag values across the doping step and produce false bands on the slice. The interpolation is done in the arsinh scale, as in picasso.
- **Current density on a face** is computed from the nodal currents in the same discretization that DEVSIM solved: edge flux × cell face area (with the `CR` correction). The sum over the anode nodes matches the contact current to six digits, and the balance inside the device is zero, which is the check. The nodal "current / area" on an unstructured mesh is noisy by tens of percent, so a smoothed ratio Σ I·w / Σ A·w with a 0.04 µm window is used, and no current is lost.
- Simpler methods do not work: a field difference near the face gives an answer that depends several-fold on the depth of the second point, and the J vector assembled on a tetrahedron from six edge fluxes gives currents through horizontal sections from 5.4 to 11.5 mA with a contact current of 9.8 mA.

### Numerics

- **A direct solver is mandatory.** Iterative GMRES under bias reports convergence on a wrong solution.
- **float128.** The Scharfetter–Gummel current is a difference of large fluxes, and the concentrations range from 10³ to 10¹⁷ cm⁻³. In double Newton stalls at 10⁻⁵, and the current at 0.1 V comes out in milliamperes. With `extended_model` + `extended_equation` convergence is quadratic down to 10⁻¹¹. It is needed only at low currents; above 0.7 V double is enough (`--fast`).
- **Memory.** On the first ISE mesh (5.8 thousand nodes): 1.3 GB, 45 s per diode on M1 (`--fast`); on the reference mesh (1.8 thousand): 0.6 GB, 150 s with float128 and 10 s with `--fast`. On a Gmsh mesh UMFPACK takes about 2.6 GB for 34 thousand nodes; the fine meshes were run on the PC — see the [workstation note](workstation_fx8320_titanx.md#english).
- **Reproducibility.** The IVs from the Mac (M1, OpenBLAS) and from the PC (FX-8320, MKL) agree to 10⁻¹⁵.

### Files and running

| | |
|---|---|
| [tools/dev_ise.py](../tools/dev_ise.py) | ISE physics, cell correction, voltage ramp |
| [tools/ise_grid.py](../tools/ise_grid.py) | the full ISE mesh: tetrahedra from faces, contacts, doping |
| [tools/voronoi3d.py](../tools/voronoi3d.py) | signed cell face areas |
| [tools/tensor_mesh.py](../tools/tensor_mesh.py) | tensor meshes on the ISE axes |
| [tools/dev3d.py](../tools/dev3d.py), [tools/mesh3d.py](../tools/mesh3d.py) | first approach: Gmsh mesh, mobility by the edge field and by \|E\| |
| [devsim/run_ise.py](../Lab3_diode_3D/devsim/run_ise.py) | main computation |
| [devsim/plot_ise.py](../Lab3_diode_3D/devsim/plot_ise.py) | verification figure and tables |
| [devsim/reference_iv.py](../Lab3_diode_3D/devsim/reference_iv.py) | digitization of the reference IV |

```bash
cd Lab3_diode_3D/devsim
python run_ise.py A --fast          # ISE mesh; comparison with ise/sA_des.plt
python run_ise.py B --fast          # B on mesh A
python run_ise.py A --tensor 1      # mesh convergence check
python plot_ise.py                  # verification figure
cd .. && python make_figures.py     # summary sheet results/devsim_ise/
```
