# -*- coding: utf-8 -*-
"""Трёхмерный дрейф-диффузионный расчёт диода. Всё в сантиметрах и вольтах.

Зачем своё: ISE не справляется со вторым диодом лабы 3 — связанный Ньютон
разваливается на крае анода. Здесь вместо него итерация Гуммеля: три уравнения
решаются по очереди, а не разом. Медленнее, но берёт то, на чём ISE встаёт.

Прибор — параллелепипед, поэтому сетка тензорная: никакого генератора,
никаких вырожденных тетраэдров.
"""

import numpy as np
from scipy.sparse import coo_matrix, identity
from scipy.sparse.linalg import spsolve

# ---------------------------------------------------------------- постоянные
Q    = 1.602176634e-19          # Кл
EPS0 = 8.8541878128e-14         # Ф/см
EPS_SI = 11.7
NI   = 1.0e10                   # см^-3, собственная концентрация кремния при 300 К
VT   = 0.025852                 # В, kT/q при 300 К
VSAT = 1.07e7                   # см/с

# Коги-Томас по легированию: mu_min, mu_max (см²/(В·с)), N_ref (см^-3), alpha.
# Те же числа берёт tools/dev3d.py — держать в одном месте.
CT_DOPING = {"n": (68.5, 1414.0, 9.2e16, 0.711),
             "p": (44.9, 470.5, 2.23e17, 0.719)}
CT_BETA = {"n": 2.0, "p": 1.0}  # показатель насыщения скорости


def mu_doping(N, kind):
    """Подвижность по Коги-Томасу: падает с ростом легирования."""
    mn, mx, nref, a = CT_DOPING[kind]
    return mn + (mx - mn) / (1.0 + (np.abs(N) / nref) ** a)


def mu_field(mu0, E, kind):
    """Насыщение скорости по Коги-Томасу: при большом поле подвижность падает,
    скорость упирается в vsat. Без этого ток не выходит на полку."""
    beta = CT_BETA[kind]
    r = mu0 * np.abs(E) / VSAT
    return mu0 / (1.0 + r ** beta) ** (1.0 / beta)


def bern(x):
    """Функция Бернулли x/(exp(x)-1), устойчиво около нуля и на хвостах."""
    x = np.asarray(x, dtype=float)
    out = np.empty_like(x)
    small = np.abs(x) < 1e-10
    big_p = x > 40.0
    big_n = x < -40.0
    mid = ~(small | big_p | big_n)
    out[small] = 1.0 - x[small] / 2.0
    out[big_p] = x[big_p] * np.exp(-x[big_p])
    out[big_n] = -x[big_n]
    xm = x[mid]
    out[mid] = xm / np.expm1(xm)
    return out


def axis(length, refine, n_coarse, ratio=0.6, n_fine=4, h_fine=None):
    """Одномерная сетка со сгущением возле точек `refine` (в см)."""
    pts = {0.0, length}
    h0 = h_fine if h_fine else length / n_coarse / 6.0
    for r in refine:
        h = h0
        for _ in range(n_fine):
            pts.add(min(length, r + h)); pts.add(max(0.0, r - h))
            h /= ratio
        pts.add(r)
    base = np.linspace(0, length, n_coarse + 1)
    pts.update(base.tolist())
    x = np.array(sorted(pts))
    return x[np.concatenate(([True], np.diff(x) > length * 1e-6))]


class Diode:
    """Диод-параллелепипед: сверху бор (p), снизу мышьяк (n), резкий переход.

    anode — прямоугольник (x0, y0, x1, y1) на верхней грани, в микронах.
    Катод — вся нижняя грань.
    """

    def __init__(self, LX=1.0, LY=3.0, LZ=0.8, NA=1.4e17, ND=1.0e17,
                 anode=(0.0, 1.0, 1.0, 2.0), nx=18, ny=28, nz=14):
        um = 1e-4
        self.LX, self.LY, self.LZ = LX * um, LY * um, LZ * um
        ax0, ay0, ax1, ay1 = [v * um for v in anode]

        self.x = axis(self.LX, [ax0, ax1], nx)
        self.y = axis(self.LY, [ay0, ay1], ny)
        self.z = axis(self.LZ, [self.LZ / 2, self.LZ], nz)
        self.nx, self.ny, self.nz = len(self.x), len(self.y), len(self.z)
        self.N = self.nx * self.ny * self.nz

        X, Y, Z = np.meshgrid(self.x, self.y, self.z, indexing="ij")
        self.C = np.where(Z > self.LZ / 2, -NA, ND)          # чистое легирование
        self.Ntot = np.where(Z > self.LZ / 2, NA, ND)

        # контакты
        self.anode_mask = ((np.abs(Z - self.LZ) < 1e-12) &
                           (X >= ax0 - 1e-12) & (X <= ax1 + 1e-12) &
                           (Y >= ay0 - 1e-12) & (Y <= ay1 + 1e-12))
        self.cath_mask = (np.abs(Z) < 1e-12)
        self.contact = self.anode_mask | self.cath_mask

        # равновесные значения на контактах
        C = self.C
        self.n_eq = 0.5 * (C + np.sqrt(C ** 2 + 4 * NI ** 2))
        self.p_eq = NI ** 2 / self.n_eq
        self.psi_bi = VT * np.arcsinh(C / (2 * NI))

        self._geometry()

    # ------------------------------------------------------------ геометрия
    def _geometry(self):
        def widths(a):
            w = np.empty_like(a)
            w[1:-1] = (a[2:] - a[:-2]) / 2
            w[0] = (a[1] - a[0]) / 2
            w[-1] = (a[-1] - a[-2]) / 2
            return w
        self.wx, self.wy, self.wz = widths(self.x), widths(self.y), widths(self.z)
        self.vol = (self.wx[:, None, None] * self.wy[None, :, None]
                    * self.wz[None, None, :])
        # площади граней и расстояния между соседями по каждой оси
        self.Ax = self.wy[None, :, None] * self.wz[None, None, :]   # грань ⟂ Ox
        self.Ay = self.wx[:, None, None] * self.wz[None, None, :]
        self.Az = self.wx[:, None, None] * self.wy[None, :, None]
        self.hx = np.diff(self.x); self.hy = np.diff(self.y); self.hz = np.diff(self.z)

    def idx(self):
        return np.arange(self.N).reshape(self.nx, self.ny, self.nz)

    def edges(self):
        """Рёбра сетки: (узел1, узел2, площадь грани, длина ребра, ось)."""
        I = self.idx()
        out = []
        A = np.broadcast_to(self.Ax, (self.nx, self.ny, self.nz))
        out.append((I[:-1].ravel(), I[1:].ravel(),
                    A[:-1].ravel(), np.broadcast_to(self.hx[:, None, None],
                                                    (self.nx - 1, self.ny, self.nz)).ravel()))
        A = np.broadcast_to(self.Ay, (self.nx, self.ny, self.nz))
        out.append((I[:, :-1].ravel(), I[:, 1:].ravel(),
                    A[:, :-1].ravel(), np.broadcast_to(self.hy[None, :, None],
                                                       (self.nx, self.ny - 1, self.nz)).ravel()))
        A = np.broadcast_to(self.Az, (self.nx, self.ny, self.nz))
        out.append((I[:, :, :-1].ravel(), I[:, :, 1:].ravel(),
                    A[:, :, :-1].ravel(), np.broadcast_to(self.hz[None, None, :],
                                                          (self.nx, self.ny, self.nz - 1)).ravel()))
        a = np.concatenate([o[0] for o in out])
        b = np.concatenate([o[1] for o in out])
        S = np.concatenate([o[2] for o in out])
        h = np.concatenate([o[3] for o in out])
        return a, b, S, h

    # ------------------------------------------------------------ сборка
    def _lap(self, coefA, coefB, a, b):
        """Матрица по рёбрам: на ребре a-b коэффициенты coefA (к b) и coefB (к a)."""
        N = self.N
        rows = np.concatenate([a, a, b, b])
        cols = np.concatenate([b, a, a, b])
        vals = np.concatenate([coefA, -coefB, coefB, -coefA])
        return coo_matrix((vals, (rows, cols)), shape=(N, N)).tocsr()

    def carriers(self, psi, phin, phip):
        """Концентрации через квазиуровни Ферми."""
        n = NI * np.exp(np.clip((psi - phin) / VT, -80, 80))
        p = NI * np.exp(np.clip((phip - psi) / VT, -80, 80))
        return n, p

    def poisson(self, psi, phin, phip, V, iters=30, tol=1e-10, clip=20.0):
        """Нелинейное уравнение Пуассона при замороженных квазиуровнях.

        Концентрации пересчитываются внутри каждой итерации — иначе якобиан
        не соответствует невязке и Ньютон вырождается в линейную сходимость.
        """
        a, b, S, h = self.edges()
        g = EPS_SI * EPS0 * S / h
        A = self._lap(g, g, a, b)
        vol = self.vol.ravel()
        fix = self.contact.ravel()
        rows = np.where(fix)[0]
        target = (self.psi_bi + np.where(self.anode_mask, V, 0.0)).ravel()

        psi = psi.copy()
        for it in range(iters):
            n, p = self.carriers(psi, phin, phip)
            F = A.dot(psi.ravel()) + Q * (p - n + self.C).ravel() * vol
            diag = -Q * (p + n).ravel() / VT * vol
            J = (A + coo_matrix((diag, (np.arange(self.N), np.arange(self.N))),
                                shape=(self.N, self.N))).tolil()
            J[rows] = 0
            J[rows, rows] = 1.0
            F[fix] = psi.ravel()[fix] - target[fix]
            d = spsolve(J.tocsr(), -F)
            d = np.clip(d, -clip * VT, clip * VT)
            psi = (psi.ravel() + d).reshape(psi.shape)
            if np.abs(d).max() < tol:
                break
        return psi, np.abs(d).max(), it + 1

    def continuity(self, psi, carrier):
        """Линейное уравнение непрерывности при замороженном потенциале."""
        a, b, S, h = self.edges()
        P = psi.ravel()
        d = (P[b] - P[a]) / VT
        Nd_edge = 0.5 * (self.Ntot.ravel()[a] + self.Ntot.ravel()[b])
        kind = "n" if carrier == "n" else "p"
        E = (P[b] - P[a]) / h                      # поле вдоль ребра
        mu = mu_field(mu_doping(Nd_edge, kind), E, kind)
        g = Q * mu * VT * S / h
        if carrier == "n":
            A = self._lap(g * bern(d), g * bern(-d), a, b)
            target = self.n_eq.ravel()
        else:
            A = self._lap(g * bern(-d), g * bern(d), a, b)
            target = self.p_eq.ravel()

        fix = self.contact.ravel()
        A = A.tolil()
        A[fix] = 0
        A[fix, np.where(fix)[0]] = 1.0
        rhs = np.zeros(self.N)
        rhs[fix] = target[fix]
        out = spsolve(A.tocsr(), rhs)
        return np.maximum(out, 1.0).reshape(psi.shape)

    def terminal_current(self, psi, n, p):
        """Ток через анод: сумма потоков по всем рёбрам, выходящим из контакта."""
        a, b, S, h = self.edges()
        P, N_, Pp = psi.ravel(), n.ravel(), p.ravel()
        an = self.anode_mask.ravel()
        d = (P[b] - P[a]) / VT
        Ntot = 0.5 * (self.Ntot.ravel()[a] + self.Ntot.ravel()[b])
        E = (P[b] - P[a]) / h
        gn = Q * mu_field(mu_doping(Ntot, "n"), E, "n") * VT * S / h
        gp = Q * mu_field(mu_doping(Ntot, "p"), E, "p") * VT * S / h
        Jn = gn * (N_[b] * bern(d) - N_[a] * bern(-d))
        Jp = gp * (Pp[a] * bern(d) - Pp[b] * bern(-d))
        I = 0.0
        sel = an[a] & ~an[b]
        I += np.sum((Jn + Jp)[sel])
        sel = an[b] & ~an[a]
        I -= np.sum((Jn + Jp)[sel])
        return I

    def gummel(self, V, state=None, outer=40, tol=1e-5, damp=0.1, verbose=False):
        """Итерация Гуммеля: Пуассон, затем электроны, затем дырки, по кругу."""
        if state is None:
            psi = self.psi_bi + np.where(self.anode_mask, V, 0.0)
            phin = np.where(self.anode_mask, V, 0.0).astype(float)
            phip = phin.copy()
        else:
            psi, phin, phip = [s.copy() for s in state]
            phin = np.where(self.anode_mask, V, phin)
            phip = np.where(self.anode_mask, V, phip)

        for k in range(outer):
            psi, _, _ = self.poisson(psi, phin, phip, V)
            n = self.continuity(psi, "n")
            p = self.continuity(psi, "p")
            phin_new = psi - VT * np.log(np.maximum(n, 1.0) / NI)
            phip_new = psi + VT * np.log(np.maximum(p, 1.0) / NI)
            err = max(np.abs(phin_new - phin).max(), np.abs(phip_new - phip).max())
            # демпфирование: не даём квазиуровням прыгать больше чем на damp вольт
            dn = np.clip(phin_new - phin, -damp, damp)
            dp = np.clip(phip_new - phip, -damp, damp)
            phin, phip = phin + dn, phip + dp
            if verbose:
                print("    Гуммель %2d: невязка %.3e В" % (k + 1, err))
            if err < tol:
                break
        n, p = self.carriers(psi, phin, phip)
        return (psi, phin, phip), n, p, self.terminal_current(psi, n, p), k + 1
