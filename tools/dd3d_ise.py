# -*- coding: utf-8 -*-
"""Самописный 3D-решатель дрейфа-диффузии с физикой ISE — на тензорной сетке, CPU или GPU.

Вторая версия tools/dd3d.py. Отличия:
  физика — та же, что в tools/dev_ise.py (и в командном файле ISE):
    подвижность по легированию — Масетти, параметры dessis для Si;
    насыщение скорости — Канали от модуля поля на ячейке (как у ISE — проверено по его
      подвижностям в узлах, experiments/ise_physics/); подвижность ребра — среднее по
      четырём ячейкам вокруг него с весом их долей грани контрольного объёма;
    сужение зоны — OldSlotboom, пополам в зоны: n = n_i·exp((psi + dEg/2 − phi_n)/V_t);
    рекомбинации нет;
  сетка — любые оси (x, y, z), в том числе оси сетки ISE с дроблением (tensor_mesh.refine):
    ячейки контрольных объёмов те же, что у DEVSIM на тензорной сетке (tools/tensor_mesh.py),
    так что два решателя сверяются на одной и той же сетке;
  счёт — итерация Гуммеля (не связанный Ньютон, как у DEVSIM и ISE — независимая проверка):
    Пуассон методом Ньютона при замороженных квазиуровнях, затем электроны, затем дырки;
  линейные системы — прямой решатель: на GPU cuDSS (nvmath), на CPU — SuperLU (scipy);
    сборка векторизована и на CuPy, и на NumPy (xp).

Единицы — см, В; оси на входе — в мкм.
"""
import time
import numpy as np

from dev_ise import MASETTI, CANALI, SLOTBOOM_OLD, NI, Q, VT, EPS

F_SMOOTH = 1.0                                   # В/см, как в dev_ise
FIELD = "kuhn"                                   # где брать |E| для насыщения: "kuhn" | "cell"
KUHN = ((0, 1, 3, 7), (0, 1, 5, 7), (0, 2, 3, 7), (0, 2, 6, 7), (0, 4, 5, 7), (0, 4, 6, 7))  # биты x=4,y=2,z=1


# ----------------------------------------------------------------- линейные решатели
class _CPU:
    def __init__(self):
        import scipy.sparse as sp
        import scipy.sparse.linalg as sl
        self.sp, self.sl = sp, sl

    def solve(self, key, rows, cols, vals, n, b):
        A = self.sp.csr_matrix((vals, (rows, cols)), shape=(n, n))
        return self.sl.spsolve(A.tocsc(), b)


class _GPU:
    """cuDSS через nvmath: шаблон матрицы каждого вида (key) раскладывается один раз,
    дальше только численное разложение. Строки и столбцы уравновешиваются (максимум 1),
    иначе статический выбор ведущих элементов портит решение (см. tools/cudss_shim.py)."""

    def __init__(self):
        import cupy as cp, cupyx, cupyx.scipy.sparse as csp, nvmath
        self.cp, self.cupyx, self.csp, self.nv = cp, cupyx, csp, nvmath
        self.slots = {}

    def solve(self, key, rows, cols, vals, n, b):
        cp = self.cp
        s = self.slots.get(key)
        if s is None:
            # шаблон: уникальные пары (строка, столбец) по возрастанию = порядок CSR;
            # inv — куда складывать каждый элемент COO (на диагонали их много — по ребру)
            keys = rows.astype(cp.int64) * n + cols.astype(cp.int64)
            uniq, inv = cp.unique(keys, return_inverse=True)
            ri = uniq // n; ci = uniq % n
            indptr = cp.concatenate([cp.zeros(1, cp.int64), cp.cumsum(cp.bincount(ri, minlength=n))])
            M = self.csp.csr_matrix((cp.zeros(uniq.size), ci.astype(cp.int32), indptr.astype(cp.int32)),
                                    shape=(n, n))
            s = dict(inv=inv.ravel(), nnz=int(uniq.size), ri=ri, ci=ci, M=M, b=cp.zeros(n), solver=None)
            self.slots[key] = s
        data = cp.bincount(s["inv"], weights=vals, minlength=s["nnz"])
        a = cp.abs(data)
        rmax = cp.zeros(n); self.cupyx.scatter_max(rmax, s["ri"], a)
        r = 1.0 / cp.where(rmax > 0, rmax, 1.0)
        data *= r[s["ri"]]
        cmax = cp.zeros(n); self.cupyx.scatter_max(cmax, s["ci"], cp.abs(data))
        c = 1.0 / cp.where(cmax > 0, cmax, 1.0)
        s["M"].data[...] = data * c[s["ci"]]
        s["b"][...] = r * b
        if s["solver"] is None:
            cp.get_default_memory_pool().free_all_blocks()
            s["solver"] = self.nv.sparse.advanced.DirectSolver(s["M"], s["b"])
            s["solver"].plan()
        s["solver"].factorize()
        return c * s["solver"].solve()


# ----------------------------------------------------------------- прибор
class Diode:
    """Параллелепипед: сверху бор (p), снизу мышьяк (n), переход на zj; анод — прямоугольник
    (x0, y0, x1, y1) на верхней грани, катод — вся нижняя грань. Оси — в мкм, должны
    содержать края анода и плоскость перехода (узлы на ней получают оба легирования, как у ISE)."""

    def __init__(self, xs, ys, zs, anode, NA=1.4e17, ND=1.0e17, zj=0.4, gpu=False, ni=NI):
        self.xp = __import__("cupy") if gpu else np
        self.lin = _GPU() if gpu else _CPU()
        xp = self.xp
        self.ni = ni
        xs, ys, zs = (np.asarray(sorted(set(np.round(a, 9)))) for a in (xs, ys, zs))
        self.xs_um, self.ys_um, self.zs_um = xs, ys, zs
        self.nx, self.ny, self.nz = len(xs), len(ys), len(zs)
        self.N = self.nx * self.ny * self.nz
        um = 1e-4
        x, y, z = xs * um, ys * um, zs * um
        X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
        eps = 1e-9
        acc = np.where(Z >= zj - eps, NA, 0.0)
        don = np.where(Z <= zj + eps, ND, 0.0)
        self.C = xp.asarray((don - acc).ravel())
        Nt = xp.asarray((don + acc).ravel())
        top, bot = np.isclose(Z, zs[-1]), np.isclose(Z, zs[0])
        an = top & (X >= anode[0] - eps) & (X <= anode[2] + eps) & (Y >= anode[1] - eps) & (Y <= anode[3] + eps)
        self.anode = xp.asarray(an.ravel()); self.cathode = xp.asarray(bot.ravel())
        self.fix = self.anode | self.cathode

        # ячейки контрольных объёмов: полуширины по осям
        def widths(a):
            w = np.empty_like(a); w[1:-1] = (a[2:] - a[:-2]) / 2; w[0] = (a[1] - a[0]) / 2; w[-1] = (a[-1] - a[-2]) / 2
            return w
        wx, wy, wz = widths(x), widths(y), widths(z)
        hx, hy, hz = np.diff(x), np.diff(y), np.diff(z)
        self.vol = xp.asarray((wx[:, None, None] * wy[None, :, None] * wz[None, None, :]).ravel())
        I = np.arange(self.N).reshape(self.nx, self.ny, self.nz)
        nx, ny, nz = self.nx, self.ny, self.nz
        # рёбра по осям: a -> b, площадь грани, длина
        ea, eb, eA, eh, eax = [], [], [], [], []
        for ax, (h, A) in enumerate(((hx, wy[:, None] * wz[None, :]), (hy, wx[:, None] * wz[None, :]),
                                     (hz, wx[:, None] * wy[None, :]))):
            sl0 = [slice(None)] * 3; sl1 = [slice(None)] * 3
            sl0[ax] = slice(0, -1); sl1[ax] = slice(1, None)
            a, b = I[tuple(sl0)], I[tuple(sl1)]
            shape = a.shape
            hh = np.broadcast_to(h.reshape([-1 if d == ax else 1 for d in range(3)]), shape)
            AA = np.broadcast_to(np.expand_dims(A, ax), shape)
            ea.append(a.ravel()); eb.append(b.ravel()); eA.append(AA.ravel()); eh.append(hh.ravel())
            eax.append(np.full(a.size, ax))
        self.ea = xp.asarray(np.concatenate(ea)); self.eb = xp.asarray(np.concatenate(eb))
        self.eA = xp.asarray(np.concatenate(eA)); self.eh = xp.asarray(np.concatenate(eh))
        self.eaxis = np.concatenate(eax)
        self.nedge = [len(e) for e in ea]
        self.hx, self.hy, self.hz = (xp.asarray(h) for h in (hx, hy, hz))
        # подвижность по полю: на тетраэдрах Куна (как DEVSIM на тензорной сетке и ISE на своей)
        # или по ячейке целиком (FIELD = "cell", проще, но |E| сглажен — ток на насыщении выше)
        self.field = FIELD
        if FIELD == "kuhn":
            self._kuhn_weights(X, Y, Z, I)
        else:
            self._cell_weights(hx, hy, hz)

        # легирование -> подвижность при слабом поле, сужение зоны, n_ie
        E_bgn, Nref, Cb = SLOTBOOM_OLD
        L = xp.log(Nt / Nref)
        self.dEg = E_bgn * (L + xp.sqrt(L * L + Cb))
        self.nie = ni * xp.exp(self.dEg / (2 * VT))
        mu_node = {k: self._masetti(Nt, k) for k in "np"}
        self.mul = {k: 0.5 * (mu_node[k][self.ea] + mu_node[k][self.eb]) for k in "np"}
        # равновесие на контактах
        self.celec = 0.5 * (self.C + xp.sqrt(self.C ** 2 + 4 * self.nie ** 2))
        self.chole = 0.5 * (-self.C + xp.sqrt(self.C ** 2 + 4 * self.nie ** 2))
        ntype = self.C > 0
        self.n_c = xp.where(ntype, self.celec, self.nie ** 2 / self.chole)
        self.p_c = xp.where(ntype, self.nie ** 2 / self.celec, self.chole)
        self.psi_c = xp.where(ntype, VT * xp.log(self.celec / self.nie), -VT * xp.log(self.chole / self.nie))

    # ------------------------------------------------------------- вспомогательное
    def _masetti(self, N, kind):
        m1, m2, mu1, pc, cr, cs, a, b, mc = MASETTI[kind]
        xp = self.xp
        return m1 * xp.exp(-pc / N) + (mc - m2) / (1 + (N / cr) ** a) - mu1 / (1 + (cs / N) ** b)

    def _cell_weights(self, hx, hy, hz):
        """Для каждого ребра — 4 соседние ячейки и их доли (h_i/2·h_j/2) / площадь грани."""
        xp = self.xp
        nx, ny, nz = self.nx, self.ny, self.nz
        ncx, ncy, ncz = nx - 1, ny - 1, nz - 1
        self.cell_shape = (ncx, ncy, ncz)
        cid = np.arange(ncx * ncy * ncz).reshape(ncx, ncy, ncz)
        out_c, out_w = [], []
        for ax in range(3):
            o1, o2 = [d for d in range(3) if d != ax]
            hs = (hx, hy, hz)
            shape = [nx, ny, nz]; shape[ax] -= 1
            idx = np.indices(shape)
            cs, ws = [], []
            for s1 in (-1, 0):
                for s2 in (-1, 0):
                    c = [idx[0], idx[1], idx[2]]
                    c[o1] = c[o1] + s1; c[o2] = c[o2] + s2
                    ok = (c[o1] >= 0) & (c[o1] < (ncx, ncy, ncz)[o1]) & (c[o2] >= 0) & (c[o2] < (ncx, ncy, ncz)[o2])
                    cc = [np.clip(c[d], 0, (ncx, ncy, ncz)[d] - 1) for d in range(3)]
                    w = np.where(ok, hs[o1][cc[o1]] / 2 * hs[o2][cc[o2]] / 2, 0.0)
                    cs.append(cid[cc[0], cc[1], cc[2]].ravel()); ws.append(w.ravel())
            W = np.stack(ws, 1); W = W / W.sum(1, keepdims=True)
            out_c.append(np.stack(cs, 1)); out_w.append(W)
        self.ecell = xp.asarray(np.concatenate(out_c)); self.ew = xp.asarray(np.concatenate(out_w))

    def _kuhn_weights(self, X, Y, Z, I):
        """Тетраэдры Куна в каждой ячейке и их доли граней Вороного по осевым рёбрам.

        Площади считаются со знаком тем же способом, что tools/voronoi3d.py (по каждому
        тетраэдру отдельно); сумма по тетраэдрам вокруг ребра — ровно площадь грани ячейки
        (проверяется). Диагонали Куна площади не имеют. Градиент на тетраэдре точный: путь
        0 -> a -> b -> 7 идёт по одному шагу вдоль каждой оси."""
        import voronoi3d
        xp = self.xp
        nx, ny, nz = self.nx, self.ny, self.nz
        P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1) * 1e-4          # см
        corner = []
        for bit in range(8):
            i, j, k = (bit >> 2) & 1, (bit >> 1) & 1, bit & 1
            corner.append(I[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k].ravel())
        corner = np.stack(corner, 1)
        tets = np.concatenate([corner[:, list(t)] for t in KUHN])            # (6·ячеек, 4)
        # шаги пути 0 -> a -> b -> 7: какая ось меняется на каждом шаге (бит)
        steps = []
        for t in KUHN:
            st = []
            for u, v in zip(t[:-1], t[1:]):
                st.append({4: 0, 2: 1, 1: 2}[u ^ v])
            steps.append(st)
        self.kuhn_tets = xp.asarray(tets)
        self.kuhn_steps = steps
        self.ncell = corner.shape[0]
        # площади со знаком по (тетраэдр, локальное ребро)
        V = [P[tets[:, q]] for q in range(4)]
        cc = voronoi3d._circ_tet(*V)
        rows, cols, w = [], [], []
        eoff = np.cumsum([0] + self.nedge)
        for (la, lb) in voronoi3d.EDGES:
            lc, ld = voronoi3d.OTHER[(la, lb)]
            m = 0.5 * (V[la] + V[lb]); e = V[lb] - V[la]
            L = np.linalg.norm(e, axis=1); e = e / L[:, None]
            fc = voronoi3d._circ_tri(V[la], V[lb], V[lc]); fd = voronoi3d._circ_tri(V[la], V[lb], V[ld])
            s = 0.5 * np.einsum("ij,ij->i", np.cross(fc - m, cc - m), e) \
                + 0.5 * np.einsum("ij,ij->i", np.cross(cc - m, fd - m), e)
            s = s * np.sign(np.einsum("ij,ij->i", np.cross(V[lc] - V[la], V[ld] - V[la]), e))
            na, nb = tets[:, la], tets[:, lb]
            lo, hi = np.minimum(na, nb), np.maximum(na, nb)
            d = hi - lo
            ax = np.where(d == ny * nz, 0, np.where(d == nz, 1, np.where(d == 1, 2, -1)))
            ok = ax >= 0                                                      # диагонали — мимо
            i0, j0, k0 = np.unravel_index(lo, (nx, ny, nz))
            eid = np.where(ax == 0, np.ravel_multi_index((np.minimum(i0, nx - 2), j0, k0), (nx - 1, ny, nz)),
                  np.where(ax == 1, np.ravel_multi_index((i0, np.minimum(j0, ny - 2), k0), (nx, ny - 1, nz)),
                           np.ravel_multi_index((i0, j0, np.minimum(k0, nz - 2)), (nx, ny, nz - 1))))
            eid = eid + eoff[np.clip(ax, 0, 2)]
            rows.append(eid[ok]); cols.append(np.arange(len(tets))[ok]); w.append(s[ok])
        rows, cols, w = np.concatenate(rows), np.concatenate(cols), np.concatenate(w)
        tot = np.bincount(rows, weights=w, minlength=eoff[-1])
        A = (self.eA.get() if hasattr(self.eA, "get") else np.asarray(self.eA))
        dev = np.abs(tot - A).max() / A.max()
        if dev > 1e-9:
            raise RuntimeError("площади Куна не сходятся с гранями ячеек: %.2e" % dev)
        self.kw_rows, self.kw_cols = xp.asarray(rows), xp.asarray(cols)
        self.kw_w = xp.asarray(w / A[rows])

    def _emag_kuhn(self, psi):
        """|E| на каждом тетраэдре Куна (точный градиент линейной функции)."""
        xp = self.xp
        t = self.kuhn_tets
        h = (self.hx, self.hy, self.hz)
        nc = self.ncell
        out = []
        for ti, (tt, st) in enumerate(zip(KUHN, self.kuhn_steps)):
            rows = slice(ti * nc, (ti + 1) * nc)
            g = [None, None, None]
            for q, ax in enumerate(st):
                a, b = t[rows, q], t[rows, q + 1]
                hh = h[ax][(xp.unravel_index(a, (self.nx, self.ny, self.nz))[ax])]
                g[ax] = (psi[b] - psi[a]) / hh
            out.append(xp.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2 + F_SMOOTH ** 2))
        return xp.concatenate(out)

    def _emag_cells(self, psi):
        """|E| на ячейке: средний по её 4 рёбрам градиент вдоль каждой оси."""
        xp = self.xp
        P = psi.reshape(self.nx, self.ny, self.nz)
        gx = (P[1:] - P[:-1]) / self.hx[:, None, None]
        gy = (P[:, 1:] - P[:, :-1]) / self.hy[None, :, None]
        gz = (P[:, :, 1:] - P[:, :, :-1]) / self.hz[None, None, :]
        Ex = 0.25 * (gx[:, :-1, :-1] + gx[:, 1:, :-1] + gx[:, :-1, 1:] + gx[:, 1:, 1:])
        Ey = 0.25 * (gy[:-1, :, :-1] + gy[1:, :, :-1] + gy[:-1, :, 1:] + gy[1:, :, 1:])
        Ez = 0.25 * (gz[:-1, :-1, :] + gz[1:, :-1, :] + gz[:-1, 1:, :] + gz[1:, 1:, :])
        return xp.sqrt(Ex ** 2 + Ey ** 2 + Ez ** 2 + F_SMOOTH ** 2).ravel()

    def mobility(self, psi, kind):
        """Подвижность на рёбрах: Масетти ребра + Канали от |E| каждой из 4 ячеек, среднее по долям."""
        vsat, beta = CANALI[kind]
        if self.field == "kuhn":
            xp = self.xp
            E = self._emag_kuhn(psi)[self.kw_cols]
            m0 = self.mul[kind][self.kw_rows]
            mu = m0 * (1 + (m0 * E / vsat) ** beta) ** (-1.0 / beta)
            return xp.bincount(self.kw_rows, weights=mu * self.kw_w, minlength=self.mul[kind].size)
        Ec = self._emag_cells(psi)[self.ecell]                    # (рёбер, 4)
        m0 = self.mul[kind][:, None]
        mu = m0 * (1 + (m0 * Ec / vsat) ** beta) ** (-1.0 / beta)
        return (mu * self.ew).sum(1)

    @staticmethod
    def bern(xp, x):
        ax = xp.abs(x)
        small = ax < 1e-8
        xs = xp.where(small, 1.0, x)
        out = xp.where(x > 0, xs * xp.exp(-xs) / (-xp.expm1(-xs)), xs / xp.expm1(xs))
        return xp.where(small, 1.0 - x / 2, out)

    # ------------------------------------------------------------- уравнения
    def carriers(self, psi, phin, phip):
        xp = self.xp
        n = self.ni * xp.exp(xp.clip((psi + self.dEg / 2 - phin) / VT, -700, 700))
        p = self.ni * xp.exp(xp.clip((phip - psi + self.dEg / 2) / VT, -700, 700))
        return n, p

    def poisson(self, psi, phin, phip, V, iters=40, tol=1e-9):
        """Нелинейный Пуассон, Ньютон; концентрации пересчитываются на каждой итерации."""
        xp = self.xp
        a, b = self.ea, self.eb
        g = EPS * self.eA / self.eh
        target = self.psi_c + xp.where(self.anode, V, 0.0)
        fix = self.fix
        nf = ~fix
        for it in range(iters):
            n, p = self.carriers(psi, phin, phip)
            F = xp.zeros(self.N)
            fl = g * (psi[b] - psi[a])
            F = F + xp.bincount(a, weights=fl, minlength=self.N) - xp.bincount(b, weights=fl, minlength=self.N)
            F = F + Q * (p - n + self.C) * self.vol
            dg = -Q * (n + p) / VT * self.vol
            rows, cols, vals = self._lap(g, g, dg, fix)
            F = xp.where(fix, psi - target, F)
            d = self.lin.solve("A", rows, cols, vals, self.N, -F)
            d = xp.clip(d, -20 * VT, 20 * VT)
            psi = psi + d
            if float(xp.abs(d).max()) < tol:
                break
        return psi, it + 1

    def _lap(self, ca, cb, diag, fix):
        """Матрица по рёбрам: строка a: +ca·x_b − cb... (общий шаблон для всех уравнений),
        строки контактов — единичные. Возвращает COO (rows, cols, vals) с фиксированным шаблоном."""
        xp = self.xp
        a, b, N = self.ea, self.eb, self.N
        nf_a, nf_b = ~fix[a], ~fix[b]
        rows = xp.concatenate([a, a, b, b, xp.arange(N)])
        cols = xp.concatenate([b, a, a, b, xp.arange(N)])
        vals = xp.concatenate([ca * nf_a, -cb * nf_a, cb * nf_b, -ca * nf_b,
                               xp.where(fix, 1.0, diag)])
        return rows, cols, vals

    def continuity(self, psi, kind, mu):
        """Линейное уравнение непрерывности при замороженных potential и подвижности.
        Поток Шарфеттера-Гуммеля по ребру a->b, электроны: J = g (n_b B(-v) − n_a B(v)),
        v = (psi_a − psi_b ± (dEg_a − dEg_b)/2)/V_t."""
        xp = self.xp
        a, b = self.ea, self.eb
        sgn = 1.0 if kind == "n" else -1.0
        v = (psi[a] - psi[b] + sgn * 0.5 * (self.dEg[a] - self.dEg[b])) / VT
        g = Q * mu * VT * self.eA / self.eh
        if kind == "n":
            ca, cb = g * self.bern(xp, -v), g * self.bern(xp, v)     # J = ca·n_b − cb·n_a
        else:
            ca, cb = g * self.bern(xp, v), g * self.bern(xp, -v)     # J = −(ca·p_b − cb·p_a)
        # строка узла a: +J, строка b: −J; J = ca·x_b − cb·x_a
        rows, cols, vals = self._lap(ca, cb, xp.zeros(self.N), self.fix)
        # диагональ некраевых узлов: сумма вкладов − уже внутри _lap (−cb в строке a, −ca в строке b)
        rhs = xp.where(self.fix, self.n_c if kind == "n" else self.p_c, 0.0)
        out = self.lin.solve("A", rows, cols, vals, self.N, rhs)
        return xp.maximum(out, 1e-30)

    def current(self, psi, n, p, mu_n, mu_p):
        """Ток анода: сумма потоков по рёбрам, выходящим из узлов анода наружу."""
        xp = self.xp
        a, b = self.ea, self.eb
        vn = (psi[a] - psi[b] + 0.5 * (self.dEg[a] - self.dEg[b])) / VT
        vp = (psi[a] - psi[b] - 0.5 * (self.dEg[a] - self.dEg[b])) / VT
        gn = Q * mu_n * VT * self.eA / self.eh
        gp = Q * mu_p * VT * self.eA / self.eh
        Jn = gn * (n[b] * self.bern(xp, -vn) - n[a] * self.bern(xp, vn))
        Jp = -gp * (p[b] * self.bern(xp, vp) - p[a] * self.bern(xp, -vp))
        J = Jn + Jp                                   # ток a -> b (положительный — в сторону b?)
        an = self.anode
        out = an[a] & ~an[b]
        inn = an[b] & ~an[a]
        # J — ток по ребру в смысле дискретизации DEVSIM (знак проверен: прямой ток диода > 0)
        return float((J * out).sum() - (J * inn).sum())

    # ------------------------------------------------------------- Гуммель и развёртка
    def initial(self):
        xp = self.xp
        psi = VT * xp.arcsinh(self.C / (2 * self.nie))
        return psi, xp.zeros(self.N), xp.zeros(self.N)

    def gummel(self, V, state, outer=400, tol=1e-6, damp=0.5, log=None, anderson=6):
        """Итерация Гуммеля по квазиуровням (phi_n, phi_p) с ускорением Андерсона.

        Сам Гуммель на высокой инжекции сходится линейно и медленно (на 2–4 В — сотни
        итераций). Андерсон (смешивание последних m шагов по МНК) — стандартное
        ускорение неподвижной точки: те же решения, в разы меньше итераций."""
        xp = self.xp
        psi, phin, phip = state
        phin = xp.where(self.anode, V, xp.where(self.cathode, 0.0, phin))
        phip = xp.where(self.anode, V, xp.where(self.cathode, 0.0, phip))
        X, G = [], []                                  # история: x_k и g(x_k) - x_k
        for k in range(outer):
            psi, _ = self.poisson(psi, phin, phip, V)
            mu_n, mu_p = self.mobility(psi, "n"), self.mobility(psi, "p")
            n = self.continuity(psi, "n", mu_n)
            p = self.continuity(psi, "p", mu_p)
            phin_new = psi + self.dEg / 2 - VT * xp.log(n / self.ni)
            phip_new = psi - self.dEg / 2 + VT * xp.log(p / self.ni)
            x = xp.concatenate([phin, phip])
            f = xp.concatenate([phin_new, phip_new]) - x
            err = float(xp.abs(f).max())
            if log:
                log("    Гуммель %3d: %.3e В" % (k + 1, err))
            if err < tol:
                break
            step = xp.clip(f, -damp, damp)
            if anderson and err < 0.05:                # Андерсон — только вблизи решения
                X.append(x); G.append(f)
                X, G = X[-(anderson + 1):], G[-(anderson + 1):]
                if len(G) > 1:
                    dG = xp.stack([G[i + 1] - G[i] for i in range(len(G) - 1)], 1)
                    dX = xp.stack([X[i + 1] - X[i] for i in range(len(X) - 1)], 1)
                    gam = xp.linalg.lstsq(dG, f, rcond=None)[0]
                    step = xp.clip(f - (dX + dG) @ gam, -damp, damp)
            else:
                X, G = [], []
            x = x + step
            phin, phip = x[:self.N], x[self.N:]
        n, p = self.carriers(psi, phin, phip)
        mu_n, mu_p = self.mobility(psi, "n"), self.mobility(psi, "p")
        return (psi, phin, phip), self.current(psi, n, p, mu_n, mu_p), k + 1, err

    def sweep(self, volts, log=print, **kw):
        state = self.initial()
        out, t0 = [], time.time()
        for V in volts:
            state, I, k, err = self.gummel(float(V), state, **kw)
            out.append((float(V), I))
            log("  V=%.3f  I=%.5e А  (%d итер., невязка %.1e, %.0f с)" % (V, I, k, err, time.time() - t0))
        return state, out

    def fields(self, state):
        """Поля в узлах на CPU — для сохранения и картинок."""
        xp = self.xp
        psi, phin, phip = state
        n, p = self.carriers(psi, phin, phip)
        mu_n, mu_p = self.mobility(psi, "n"), self.mobility(psi, "p")
        g = lambda a: a.get() if hasattr(a, "get") else np.asarray(a)
        # плотность тока на рёбрах (a -> b), А/см² — для вектора J в узлах
        a, b = self.ea, self.eb
        vn = (psi[a] - psi[b] + 0.5 * (self.dEg[a] - self.dEg[b])) / VT
        vp = (psi[a] - psi[b] - 0.5 * (self.dEg[a] - self.dEg[b])) / VT
        Jn = Q * mu_n * VT / self.eh * (n[b] * self.bern(xp, -vn) - n[a] * self.bern(xp, vn))
        Jp = -Q * mu_p * VT / self.eh * (p[b] * self.bern(xp, vp) - p[a] * self.bern(xp, -vp))
        return dict(psi=g(psi).reshape(self.nx, self.ny, self.nz), n=g(n).reshape(self.nx, self.ny, self.nz),
                    p=g(p).reshape(self.nx, self.ny, self.nz), C=g(self.C).reshape(self.nx, self.ny, self.nz),
                    x=self.xs_um * 1e-4, y=self.ys_um * 1e-4, z=self.zs_um * 1e-4,
                    edge_j=g(Jn + Jp), edge_a=g(a), edge_b=g(b), edge_axis=self.eaxis)
