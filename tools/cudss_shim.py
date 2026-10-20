# -*- coding: utf-8 -*-
"""Прямой решатель DEVSIM на GPU: cuDSS (NVIDIA) через nvmath-python, FP64.

    import cudss_shim; cudss_shim.install()     # после import devsim, до solve()

DEVSIM собирает якобиан на CPU (в том числе в float128), а разложение — самая дорогая
часть на мелкой 3D-сетке — уходит на видеокарту. Протокол тот же, что у вшитого
devsim/umfpack/umfshim.py: DEVSIM зовёт solver_callback с action = init / factor / solve
и отдаёт матрицу в CSC.

Проверено на TITAN X Pascal (sm_61): разложение 3D 7-точечной матрицы на 216 тыс.
неизвестных — 2.4 с, на 512 тыс. — 12 с (experiments/gpu_precision/bench_cudss.py).
"""
import array
import numpy as np
import cupy as cp
import cupyx
import cupyx.scipy.sparse as csp
import devsim
import nvmath

STATS = {"factor": 0, "analysis": 0}


class _Solver:
    def __init__(self, n, transpose):
        self.n, self.transpose = n, transpose
        self.solver = None          # nvmath DirectSolver, живёт, пока не сменится шаблон матрицы
        self.A = None               # CSR на GPU, данные обновляются на месте
        self.perm = None            # порядок CSC -> CSR для данных
        self.b = None

    def factor(self, Ap, Ai, Ax, is_same_symbolic, **_):
        Ax = cp.asarray(np.array(Ax, dtype=np.float64))        # array.array из DEVSIM — по буферу
        if self.solver is None or not is_same_symbolic:
            self.close()
            Ap = cp.asarray(np.array(Ap, dtype=np.int64))
            Ai = cp.asarray(np.array(Ai, dtype=np.int64))
            n = self.n
            # CSC(A) -> CSR(A) (или CSR(A^T), если DEVSIM просит транспонированную систему);
            # перестановку данных запоминаем, чтобы дальше обновлять значения без пересборки
            idx = cp.arange(Ax.size, dtype=cp.float64)
            C = csp.csc_matrix((idx, Ai, Ap), shape=(n, n))
            R = C.T.tocsr() if self.transpose else C.tocsr()
            R.sort_indices()
            self.perm = R.data.astype(cp.int64)
            self.cols = R.indices.astype(cp.int64)
            self.rows = cp.repeat(cp.arange(n, dtype=cp.int64), cp.diff(R.indptr).astype(cp.int64))
            self.A = csp.csr_matrix((self._equilibrate(Ax[self.perm]), R.indices.astype(cp.int32),
                                     R.indptr.astype(cp.int32)), shape=(n, n))
            self.b = cp.zeros(n)
            self.solver = nvmath.sparse.advanced.DirectSolver(self.A, self.b)
            self.solver.plan()
            STATS["analysis"] += 1
        else:
            self.A.data[...] = self._equilibrate(Ax[self.perm])
        self.solver.factorize()
        STATS["factor"] += 1

    def _equilibrate(self, data):
        """Масштаб строк и столбцов: максимум |a_ij| в каждой — 1.

        Без этого cuDSS (статический выбор ведущих элементов) губит строки уравнения
        Пуассона: в сантиметрах их коэффициенты ~1e-16 против единиц в строках контактов,
        и «малые» ведущие элементы подменяются — решение выходит неверным.
        """
        n = self.n
        a = cp.abs(data)
        rmax = cp.zeros(n); cupyx.scatter_max(rmax, self.rows, a)
        self.r = 1.0 / cp.where(rmax > 0, rmax, 1.0)
        data = data * self.r[self.rows]
        cmax = cp.zeros(n); cupyx.scatter_max(cmax, self.cols, cp.abs(data))
        self.c = 1.0 / cp.where(cmax > 0, cmax, 1.0)
        return data * self.c[self.cols]

    def solve(self, b, **_):
        self.b[...] = self.r * cp.asarray(np.array(b, dtype=np.float64))
        x = self.c * self.solver.solve()
        return array.array("d", cp.asnumpy(x).tobytes())

    def close(self):
        if self.solver is not None:
            self.solver.free()
            self.solver = None


def _callback(**kw):
    act = kw["action"]
    if act == "init":
        so = _Solver(kw["n"], kw["transpose"])
        return {"solver_object": so, "matrix_format": "csc", "status": True, "message": ""}
    so = kw["solver_object"]
    if kw.get("is_complex"):
        return {"status": False, "message": "cudss_shim: комплексные системы не поддерживаются"}
    try:
        if act == "factor":
            so.factor(**kw)
            return {"status": True, "message": ""}
        if act == "solve":
            return {"status": True, "message": "", "x": so.solve(**kw)}
    except Exception as e:                    # пусть DEVSIM увидит ошибку как срыв решения
        return {"status": False, "message": "cudss_shim: %r" % (e,)}
    raise RuntimeError("cudss_shim: неизвестное действие " + act)


def install():
    devsim.set_parameter(name="direct_solver", value="custom")
    devsim.set_parameter(name="solver_callback", value=_callback)
    return "cuDSS (nvmath %s) на %s" % (nvmath.__version__,
                                        cp.cuda.runtime.getDeviceProperties(0)["name"].decode())
