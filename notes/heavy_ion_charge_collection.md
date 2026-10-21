# Charge Collection After Heavy-Ion Strikes: A Material Parameter Sweep in a 2001 TCAD Solver

[Русский](#русский) · [English](#english) · [← к README](../README.md)

## Русский

### Развёртка параметров материала в TCAD-решателе 2001 года

Это продолжение [заметки про запуск ISE TCAD на маке](ise_tcad_apple_silicon.md): там была инфраструктура, здесь — что вышло из
реального использования. Коротко: физические результаты скромные, а самым
полезным оказался урок о том, как легко обмануть себя настройками
интегрирования по времени.

### Постановка

Двумерный кремниевый диод с резким p-n переходом. Сетка намеренно маленькая —
**162 вершины, 282 треугольника**, — чтобы один прогон стоил минуты, а не часы.

```
прибор      3.0 × 1.0 мкм
анод        1.0 мкм шириной, верхняя грань (частичный контакт)
катод       вся нижняя грань
переход     посередине по глубине
смещение    −2 В, обратное
```

Анод закрывает только треть верхней грани. Это окажется важным.

Удар иона задаётся встроенным источником тяжёлых ионов
([validation/see_des.cmd](../experiments/heavy_ion/validation/see_des.cmd)):

```
HeavyIon (
    Direction = (0,1)
    Location  = (0.0,-0.5)
    Time      = 100e-12
    Length    = 1e-4        ! см, то есть 1 мкм
    Wt_hi     = 0.05e-4     ! см, то есть радиус трека 0.05 мкм
    LET_f     = 0.2         ! пКл/мкм
    Gaussian
    PicoCoulomb
)
```

Две ловушки с единицами, каждая стоила по неудачному прогону: `Length` и
`Wt_hi` задаются **в сантиметрах**, не в микронах, а `LET_f` по умолчанию
в парах на см³, если не добавить ключевое слово `PicoCoulomb`. Ошибись в любой —
и модель молча почти ничего не генерирует. Ни предупреждения, ни ошибки —
просто плоская кривая тока.

### Проверка 1: работает ли источник иона

Базовый прогон на обычном кремнии. Трек оставляет 0.2 пКл/мкм на пути в 1 мкм,
то есть **0.2 пКл всего**.

![Ток анода во времени, логарифмическая шкала](../experiments/heavy_ion/validation/seu_transient.png)

| величина | значение |
|---|---|
| ток утечки до удара | 1.5·10<sup>−15</sup> А |
| пик тока | −5.41 мА при t = 0.1055 нс |
| возврат к утечке | к ≈ 0.6 нс |
| **собранный заряд** | **0.176 пКл** |
| **эффективность сбора** | **88%** |

Ток прыгает на двенадцать порядков и спадает за пару сотен пикосекунд.
88% выделенного заряда доходит до анода, остальное рекомбинирует. И форма, и
величина такие, как и следует ожидать, — ради этого базовый прогон и делается.

Файлы: [see_des.cmd](../experiments/heavy_ion/validation/see_des.cmd),
[see_des.plt](../experiments/heavy_ion/validation/see_des.plt) (ток),
[ion_see_des.plt](../experiments/heavy_ion/validation/ion_see_des.plt).

### Проверка 2: можно ли выдумывать материалы

Решатель грузит параметры материалов из текстовой библиотеки, и расчёт может
переопределить любой из них маленьким файлом
([bandgap/egA.par](../experiments/heavy_ion/bandgap/egA.par)):

```
Material = "Silicon" {
    Bandgap {
        Eg0 = 1.40000   # [eV]
        ...
    }
}
```

Заменяются только перечисленные блоки, всё остальное берётся из библиотеки.
Поэтому гипотетические материалы делаются легко: берёшь кремний, меняешь нужные
числа, остальное не трогаешь.

Чтобы проверить, что это действительно меняет физику — и меняет на правильную
величину, — тот же диод посчитан дважды, отличие только в ширине запрещённой
зоны.

![ВАХ при двух ширинах запрещённой зоны, логарифмическая шкала](../experiments/heavy_ion/bandgap/bandgap_test.png)

| смещение | I при E<sub>g</sub> = 1.17 эВ | I при E<sub>g</sub> = 1.40 эВ | отношение |
|---|---|---|---|
| 0.5 В | 3.39·10<sup>−9</sup> А | 4.66·10<sup>−13</sup> А | **7260** |
| 1.0 В | 7.85·10<sup>−4</sup> | 3.96·10<sup>−5</sup> | 19.8 |
| 1.5 В | 2.93·10<sup>−3</sup> | 2.10·10<sup>−3</sup> | 1.39 |
| 4.0 В | 4.70·10<sup>−3</sup> | 4.67·10<sup>−3</sup> | 1.01 |

При малом смещении ток пропорционален n<sub>i</sub>², то есть exp(−E<sub>g</sub>/kT). Для
ΔE<sub>g</sub> = 0.2304 эВ при 300 К это даёт отношение

exp(0.2304 / 0.02585) = 7420

против измеренных **7260** — совпадение в пределах 2%. При большом смещении
кривые сходятся: там ток ограничен последовательным сопротивлением, которому
до ширины зоны дела нет.

Значит, механизм подмены работает, и работает количественно.

Файлы: [desA.cmd](../experiments/heavy_ion/bandgap/desA.cmd), [desB.cmd](../experiments/heavy_ion/bandgap/desB.cmd),
[egA.par](../experiments/heavy_ion/bandgap/egA.par), [egB.par](../experiments/heavy_ion/bandgap/egB.par),
[pA.plt](../experiments/heavy_ion/bandgap/pA.plt), [pB.plt](../experiments/heavy_ion/bandgap/pB.plt).

### Физика, которую нельзя забыть

Источник тяжёлых ионов задаёт выделенный **заряд** на микрон, а не выделенную
**энергию**. Если менять ширину зоны при фиксированном `LET_f`, неявно
утверждается, что широкозонный материал рождает столько же электрон-дырочных
пар на единицу пути, сколько узкозонный. Это не так.

Энергия на одну пару подчиняется правилу Кляйна:

E<sub>pair</sub> ≈ 2.8·E<sub>g</sub> + 0.6  [эВ]

поэтому при фиксированной выделенной энергии число пар падает как
1/(2.8·E<sub>g</sub> + 0.6). На взятом диапазоне это в **2.67 раза** меньше носителей при
E<sub>g</sub> = 3.3 эВ, чем в кремнии. Во всех прогонах ниже `LET_f` пересчитан
соответственно.

Пропустите это — и широкозонные материалы будут выглядеть незаслуженно хорошо.

### Развёртка

Девять точек: ширина запрещённой зоны × подвижность электронов, всё остальное
фиксировано — геометрия, сетка, смещение, место удара, выделенная энергия.

```
Eg  ∈ {1.1, 2.2, 3.3}  эВ
µn  ∈ {200, 900, 3000} см²/(В·с)
µp  = µn / 3
```

Точка считается около шести минут, вся развёртка — меньше часа без присмотра.

![Эффективность сбора от подвижности, по кривой на каждую ширину зоны](../experiments/heavy_ion/sweep/map_efficiency.png)

**Эффективность сбора, %**

| | µ=200 | µ=900 | µ=3000 | разброс |
|---|---|---|---|---|
| E<sub>g</sub> = 1.1 эВ | 94.2 | 88.9 | 83.9 | 10.3 п.п. |
| E<sub>g</sub> = 2.2 эВ | 92.0 | 88.5 | 86.9 | 5.1 п.п. |
| E<sub>g</sub> = 3.3 эВ | 95.9 | 87.2 | 87.8 | 8.7 п.п. |

**Собранный заряд, пКл**

| | µ=200 | µ=900 | µ=3000 |
|---|---|---|---|
| E<sub>g</sub> = 1.1 эВ | 0.1913 | 0.1805 | 0.1704 |
| E<sub>g</sub> = 2.2 эВ | 0.1016 | 0.0978 | 0.0961 |
| E<sub>g</sub> = 3.3 эВ | 0.0728 | 0.0662 | 0.0666 |

**Что делают два параметра.** Они действуют на **разные наблюдаемые**, и это
главный результат:

- **Ширина зоны задаёт абсолютный сигнал.** Собранный заряд падает в 2.73 раза
  от 1.1 до 3.3 эВ, почти целиком через правило Кляйна. Эффективность почти не
  меняется.
- **Подвижность задаёт эффективность.** Пять–десять процентных пунктов на
  пятнадцатикратном диапазоне подвижности, при любой ширине зоны. Абсолютный
  заряд почти не меняется.

Если подгонять параметры под измеренную *высоту* импульса, точно знать надо
ширину зоны. Если под собранную *долю* — подвижность. Усилия на не тот параметр
уходят впустую.

**Контринтуитивная часть.** Эффективность сбора **падает** с ростом
подвижности. Наивно ждёшь обратного: быстрые носители должны успеть уйти до
рекомбинации.

Установленного механизма нет. Главный кандидат — диффузионное
расплывание. Коэффициент диффузии следует за подвижностью по соотношению
Эйнштейна, D = µkT/q, так что в пятнадцать раз большая подвижность — это в
пятнадцать раз большая диффузия. Плазма трека расползается вбок как √(4Dt), и
при аноде в 1 мкм на приборе шириной 3 мкм большая доля носителей уходит из
области сбора и рекомбинирует.

Гипотеза дёшево проверяется: расширить анод на всю грань — эффект должен
уменьшиться. Здесь не сделано.

### Часть, которая на самом деле стоила дня

Одна точка сетки — E<sub>g</sub> = 3.3 эВ, µ = 200, угол, где плазма живёт дольше всего
и вытягивается медленнее всего, — дала **четыре разных ответа** при четырёх
схемах интегрирования:

| схема | результат | что было не так | файлы |
|---|---|---|---|
| окно 1 нс, шаг 20 пс | 70.7% | хвост обрезан: на краю окна ещё течёт 33% пикового тока | [m20.cmd](../experiments/heavy_ion/sweep/m20.cmd) |
| окно 40 нс, шаг 400 пс | 98.8% | инжекция не разрешена: удар длится пикосекунды, шаг 400 пс через него перешагивает | [Lm20.cmd](../experiments/heavy_ion/sweep/Lm20.cmd) |
| две стадии, вторая грубая | 1671% | решатель прервался — *«Step is too small»*, — оставив частичный, бессмысленный интеграл | [Tm20.cmd](../experiments/heavy_ion/sweep/Tm20.cmd) |
| две стадии, вторая мелкая | **95.9%** | остаточный ток 1.8·10<sup>−14</sup> от пика, интеграл полный | [Sm20.cmd](../experiments/heavy_ion/sweep/Sm20.cmd) |

Правильное значение — 95.9%, и это делает угол *лучшей* точкой карты. Первая
попытка показывала его худшей с большим отрывом.

Из этого следуют две вещи.

**Схема интегрирования может перевесить то, что измеряешь.** Разброс между
четырьмя артефактами больше, чем разброс между многими опубликованными
наборами параметров реальных материалов. Сравнение материалов на одной
фиксированной схеме по времени может оказаться сравнением схемы, а не
материалов.

**Цена правильного ответа неодинакова по пространству параметров.** Восемь из
девяти точек сошлись на первой схеме. Девятой понадобилось четыре попытки — и
это не случайная точка, а физически самый жёсткий угол. Развёртки на
одинаковых настройках поэтому систематически менее точны именно там, где
физика интереснее всего.

Ни одно из наблюдений не глубокое. Но на оба легко попасться: первый
артефакт дал седловидную карту с переворотом тренда, которая выглядела как
находка. А это был обрезанный хвост.

**Проверка, которая это ловит.** Дёшево и достаточно: для каждого прогона
показывать остаточный ток в конце окна в долях пикового.

```
          µ=200      µ=900     µ=3000
Eg=1.1    1.4e-05    1.2e-12   4.0e-13
Eg=2.2    5.1e-07    2.2e-14   3.0e-15
Eg=3.3    3.3e-01 ←  9.6e-15   1.9e-16
```

Единственное плохое число бросается в глаза сразу. Две точки дополнительно
пересчитаны с окном в шестьдесят раз длиннее и воспроизвели прежние значения до
десятой доли процента — это и делает остальную таблицу надёжной.

### Ограничения

Прямо, потому что они не маленькие:

- **Сетка параметров 3×3.** Хватает для трендов, не для поверхности отклика.
- **Параметры менялись независимо.** В реальных материалах ширина зоны,
  диэлектрическая проницаемость и подвижность связаны; некоторые из этих
  сочетаний не могут существовать.
- **Диапазоны выбраны руками**, а не взяты из разброса по литературе.
- **Подвижность дырок взята как треть подвижности электронов** без
  обоснования, кроме правдоподобия.
- **Одна геометрия.** Эффект подвижности, скорее всего, связан с частичным
  анодом, так что на другой прибор ничего не переносится без проверки.
- **Нет экспериментальной проверки**, и в такой постановке её не может быть.

Это пилот, а не результат, на котором можно строить.

### Воспроизводимость

Всё запускается из блокнота Jupyter на маке; решатель работает в виртуалке и
управляется через сетевой шелл. Вся развёртка из девяти точек — меньше часа
счёта без присмотра.

Сам решатель быстрый: две итерации Ньютона на шаг по времени, по 0.13 с каждая,
на этой сетке. Длинные прогоны дёшевы, если не давать им умирать — а это, как
описано в [первой заметке](ise_tcad_apple_silicon.md), было отдельной проблемой.

Файлы развёртки — [experiments/heavy_ion/sweep/](../experiments/heavy_ion/sweep/):

| | |
|---|---|
| [runs.json](../experiments/heavy_ion/sweep/runs.json) | план: метка точки, E<sub>g</sub>, µ, пересчитанный `LET_f` |
| `m00.cmd` … `m22.cmd`, `m00.par` … `m22.par` | девять точек: задание решателя и подмена параметров материала (метка `mXY`: X — номер E<sub>g</sub>, Y — номер µ) |
| `Lm*.cmd`, `Tm*.cmd`, [Sm20.cmd](../experiments/heavy_ion/sweep/Sm20.cmd) | длинное окно, две стадии с грубой и с мелкой второй стадией |
| `i_m*.plt`, `Lm*.plt`, `Tm*.plt`, `Sm20.plt` | токи во времени |
| [results.json](../experiments/heavy_ion/sweep/results.json), [results_two.json](../experiments/heavy_ion/sweep/results_two.json), [final.json](../experiments/heavy_ion/sweep/final.json) | собранный заряд, эффективность, пик, остаточный ток |
| [runall.bat](../experiments/heavy_ion/sweep/runall.bat), [runlong.bat](../experiments/heavy_ion/sweep/runlong.bat), [runtwo.bat](../experiments/heavy_ion/sweep/runtwo.bat), [runs4.bat](../experiments/heavy_ion/sweep/runs4.bat) | батники для запуска через `at` |

Сетка во всех прогонах — 2D-диод 3 × 1 мкм (`sh1_msh.grd` + `sh1_msh.dat`,
162 узла), собранный как в лабе 1. Сам файл сетки остался внутри виртуалки и
сюда не выгружен; чтобы повторить, его надо построить из
[Lab1_diode_2D/ise/sh1.bnd](../Lab1_diode_2D/ise/sh1.bnd) и
[sh1.cmd](../Lab1_diode_2D/ise/sh1.cmd) с толщиной 1 мкм.

### Стоит ли продолжать

Как исследование — нет. Находки тонкие, механизм не объяснён, а методические
наблюдения — проверяй окно интегрирования, проверяй шаг — это уроки, а не
открытия.

Как упражнение — стоило. Стенд работает, конвейер переиспользуется, а
решатель, которому уже можно голосовать, вполне способен давать количественно
верную физику — если аккуратно обращаться с единицами, со временем и с
собственными допущениями.

---

## English

### A material parameter sweep in a 2001 TCAD solver

This is a follow-up to an earlier note about bringing ISE TCAD 7.0 — a semiconductor device simulator from 2001 — back to life on an ARM Mac under emulation. That note covered the infrastructure. This one covers what came out of actually using it.

Short version: the simulation results are modest, and the most useful thing the study produced was a lesson about how easy it is to fool yourself with transient integration settings.

------------------------------------------------------------------------

### The setup

A two-dimensional silicon diode with an abrupt p-n junction. The mesh is deliberately small — **162 vertices, 282 triangles** — so that a single run costs minutes rather than hours.

```
device      3.0 × 1.0 µm
anode       1.0 µm wide, top face (partial contact)
cathode     full bottom face
junction    at mid-depth
bias        −2 V reverse
```

The anode covers only a third of the top face. This turns out to matter.

Ion strikes are modelled with the solver's built-in heavy-ion source:

```
HeavyIon (
    Direction = (0,1)
    Location  = (0.0,-0.5)
    Time      = 100e-12
    Length    = 1e-4        ! cm, i.e. 1 µm
    Wt_hi     = 0.05e-4     ! cm, i.e. 0.05 µm track radius
    LET_f     = 0.2         ! pC/µm
    Gaussian
    PicoCoulomb
)
```

Two units traps worth flagging, because both cost me a failed run: `Length` and `Wt_hi` are **centimetres**, not microns, and `LET_f` defaults to pairs/cm³ unless you add the `PicoCoulomb` keyword. Get either wrong and the model silently generates almost nothing — no warning, no error, just a flat current trace.

------------------------------------------------------------------------

### Validation 1: does the ion source work?

Baseline run on plain silicon. The track deposits 0.2 pC/µm over a 1 µm path, so **0.2 pC total**.

![Anode current vs time, log scale](../experiments/heavy_ion/validation/seu_transient.png)

*Anode current vs time, log scale*

| Quantity                  | Value                     |
|---------------------------|---------------------------|
| Pre-strike leakage        | 1.5 × 10⁻¹⁵ A             |
| Peak current              | −5.41 mA at t = 0.1055 ns |
| Back to leakage           | by ≈ 0.6 ns               |
| **Collected charge**      | **0.176 pC**              |
| **Collection efficiency** | **88 %**                  |

The current jumps twelve orders of magnitude and decays within a couple of hundred picoseconds. Eighty-eight per cent of the deposited charge reaches the anode; the rest recombines. Both the shape and the magnitude are what you would expect, which is the point of running a baseline.

------------------------------------------------------------------------

### Validation 2: can we invent materials?

The solver loads material parameters from a plain-text library, and a simulation can override any of them through a small file:

```
Material = "Silicon" {
    Bandgap {
        Eg0 = 1.40000   # [eV]
        ...
    }
}
```

Only the blocks you list are replaced; everything else falls back to the library. That makes hypothetical materials easy: take silicon, change the numbers you care about, leave the rest alone.

To check that this actually changes the physics — and changes it by the right amount — the same diode was run twice with nothing different but the bandgap.

![I-V curves for two bandgaps, log scale](../experiments/heavy_ion/bandgap/bandgap_test.png)

*I-V curves for two bandgaps, log scale*

| Bias  | I at Eg = 1.17 eV | I at Eg = 1.40 eV | Ratio    |
|-------|-------------------|-------------------|----------|
| 0.5 V | 3.39 × 10⁻⁹ A     | 4.66 × 10⁻¹³ A    | **7260** |
| 1.0 V | 7.85 × 10⁻⁴       | 3.96 × 10⁻⁵       | 19.8     |
| 1.5 V | 2.93 × 10⁻³       | 2.10 × 10⁻³       | 1.39     |
| 4.0 V | 4.70 × 10⁻³       | 4.67 × 10⁻³       | 1.01     |

At low bias the current is proportional to nᵢ², which scales as exp(−Eg/kT). For ΔEg = 0.2304 eV at 300 K that predicts a ratio of

```
exp(0.2304 / 0.02585) = 7420
```

against a measured **7260** — agreement within 2 %. At high bias the curves converge, because there the current is limited by series resistance, which does not care about the bandgap.

So the override mechanism works, and it works quantitatively.

------------------------------------------------------------------------

### One piece of physics you must not forget

The heavy-ion source specifies deposited **charge** per micron, not deposited **energy**. Sweep the bandgap while holding `LET_f` fixed and you are implicitly claiming that a wide-gap material generates as many electron-hole pairs per unit path as a narrow-gap one. It does not.

The energy needed per pair follows Klein's rule:

```
E_pair ≈ 2.8 · Eg + 0.6   [eV]
```

so at fixed deposited energy the pair count scales as 1/(2.8·Eg + 0.6). Across the range swept here that is a factor of **2.67** fewer carriers at Eg = 3.3 eV than in silicon. Every run below rescales `LET_f` accordingly.

Skip this and wide-bandgap materials look artificially good.

------------------------------------------------------------------------

### The sweep

Nine points: bandgap × electron mobility, everything else held fixed — geometry, mesh, bias, strike position, deposited energy.

```
Eg   ∈ {1.1, 2.2, 3.3}  eV
µn   ∈ {200, 900, 3000} cm²/(V·s)
µp   = µn / 3
```

Each point takes about six minutes. The full sweep ran unattended in under an hour.

![Collection efficiency vs mobility, one curve per bandgap](../experiments/heavy_ion/sweep/map_efficiency.png)

*Collection efficiency vs mobility, one curve per bandgap*

**Collection efficiency, %**

|             | µ=200 | µ=900 | µ=3000 | spread  |
|-------------|-------|-------|--------|---------|
| Eg = 1.1 eV | 94.2  | 88.9  | 83.9   | 10.3 pp |
| Eg = 2.2 eV | 92.0  | 88.5  | 86.9   | 5.1 pp  |
| Eg = 3.3 eV | 95.9  | 87.2  | 87.8   | 8.7 pp  |

**Collected charge, pC**

|             | µ=200  | µ=900  | µ=3000 |
|-------------|--------|--------|--------|
| Eg = 1.1 eV | 0.1913 | 0.1805 | 0.1704 |
| Eg = 2.2 eV | 0.1016 | 0.0978 | 0.0961 |
| Eg = 3.3 eV | 0.0728 | 0.0662 | 0.0666 |

#### What the two parameters do

They act on **different observables**, and that separation is the main result:

- **Bandgap sets the absolute signal.** Collected charge falls 2.73× going from 1.1 to 3.3 eV, almost entirely through Klein's rule. Efficiency barely moves.
- **Mobility sets the efficiency.** Five to ten percentage points across a fifteen-fold mobility range, at every bandgap tested. Absolute charge barely moves.

If you are fitting parameters to match a measured pulse *height*, the bandgap is what you need to know accurately. If you are matching collected *fraction*, it is the mobility. Effort spent on the wrong one is wasted.

#### The counter-intuitive part

Collection efficiency **decreases** as mobility rises. The naive expectation is the opposite: faster carriers should escape before recombining.

I do not have an established mechanism. The leading candidate is diffusive spreading. The diffusion coefficient follows mobility through the Einstein relation, D = µkT/q, so fifteen times the mobility means fifteen times the diffusivity. The track plasma spreads sideways as √(4Dt), and with a 1 µm anode on a 3 µm wide device, a larger share of the carriers wanders out of the collecting region and recombines.

That hypothesis is cheap to test: widen the anode to the full face and the effect should shrink. Not done here.

------------------------------------------------------------------------

### The part that actually cost a day

One grid point — Eg = 3.3 eV, µ = 200, the corner where the plasma lives longest and is extracted slowest — returned **four different answers** under four integration schemes:

| Scheme | Result | What was wrong |
|----|----|----|
| 1 ns window, 20 ps step | 70.7 % | tail truncated: 33 % of peak current still flowing at the window edge |
| 40 ns window, 400 ps step | 98.8 % | injection unresolved: the strike lasts picoseconds and a 400 ps step steps over it |
| two-stage, coarse second stage | 1671 % | solver aborted — *"Step is too small"* — leaving a partial, meaningless integral |
| two-stage, fine second stage | **95.9 %** | residual current 1.8 × 10⁻¹⁴ of peak; integral complete |

The correct value is 95.9 %, which makes that corner the *best* point on the map. The first attempt had it as the worst by a wide margin.

Two things follow.

**The integration scheme can outweigh the thing you are measuring.** The spread across those four artefacts is larger than the spread between many published parameter sets for real materials. A material comparison run on a single fixed time scheme can be dominated by the scheme rather than by the materials.

**The cost of a correct answer is not uniform across parameter space.** Eight of nine points converged on the first scheme. The ninth needed four attempts — and it was not a random point but the physically stiffest corner. Sweeps run at uniform settings are therefore systematically less accurate exactly where the physics is most interesting.

Neither observation is deep. Both are easy to fall for: the first artefact produced a saddle-shaped map with a trend reversal, which looked like a finding. It was a truncated tail.

#### The check that catches it

Cheap and sufficient: for every run, report the residual current at the end of the window as a fraction of the peak.

```
        µ=200      µ=900     µ=3000
Eg=1.1  1.4e-05    1.2e-12   4.0e-13
Eg=2.2  5.1e-07    2.2e-14   3.0e-15
Eg=3.3  3.3e-01 ←  9.6e-15   1.9e-16
```

The one bad number stands out immediately. Two points were additionally re-run with a sixty-times-longer window and reproduced their original values to a tenth of a per cent, which is what makes the rest of the table trustworthy.

------------------------------------------------------------------------

### Limits of this study

Stated plainly, because they are not small:

- **The grid is 3×3.** Enough for trends, not for a response surface.
- **Parameters were swept independently.** In real materials bandgap, permittivity and mobility are correlated; some of these combinations cannot exist.
- **Ranges were chosen by hand**, not taken from literature spreads.
- **Hole mobility was set to one third of the electron mobility** with no justification beyond plausibility.
- **One geometry.** The mobility effect is very likely tied to the partial anode, so nothing here transfers to another device unchecked.
- **No experimental validation**, and none possible with this setup.

This is a pilot, not a result to build on.

------------------------------------------------------------------------

### Reproducibility

Everything is scripted from a Jupyter notebook on the host machine; the solver runs in the virtual machine and is driven over a network shell. Total wall time for the nine-point sweep was under an hour of unattended computation.

The solver itself is fast: two Newton iterations per timestep, 0.13 s each, on this mesh. Long runs are cheap once they are prevented from dying — which, as the previous note describes, was its own separate problem.

Tooling written along the way:

- a DF-ISE parser, because the solver's output format encodes elements by edges rather than vertices and splits fields across regions
- a plotting layer reproducing the original visualiser's conventions
- a parameter-file generator for material sweeps
- a network shell client with prompt synchronisation

------------------------------------------------------------------------

### Would I take this further?

Not as research. The findings are thin, the mechanism is unexplained, and the methodological observations — check your integration window, check your timestep — are lessons rather than discoveries.

As an exercise it was worth it. The stand works, the pipeline is reusable, and a solver old enough to vote turned out to be perfectly capable of producing quantitatively correct physics, provided you are careful about units, about time integration, and about not believing the first plot that looks interesting.
