# -*- coding: utf-8 -*-
"""cuDSS (прямой разреженный решатель NVIDIA) на TITAN X Pascal: 3D 7-точечный шаблон.

Матрица — лапласиан плюс диагональ со случайным контрастом коэффициентов
(как у уравнения непрерывности: проводимость рёбер гуляет на порядки).
Меряет время solve (анализ + разложение + решение), память GPU и невязку в FP64.

    python bench_cudss.py 40 60 80 100     # стороны куба
"""
import sys, time
import numpy as np
import cupy as cp
import cupyx.scipy.sparse as csp
import nvmath


def matrix(n, contrast=8.0, seed=1):
    """M-матрица на кубе n^3: веса рёбер 10^U(-contrast/2, contrast/2)."""
    rng = np.random.default_rng(seed)
    N = n ** 3
    idx = np.arange(N).reshape(n, n, n)
    rows, cols, vals = [], [], []
    diag = np.zeros(N)
    for ax in range(3):
        a = np.take(idx, range(n - 1), axis=ax).ravel()
        b = np.take(idx, range(1, n), axis=ax).ravel()
        w = 10.0 ** rng.uniform(-contrast / 2, contrast / 2, a.size)
        rows += [a, b]; cols += [b, a]; vals += [-w, -w]
        np.add.at(diag, a, w); np.add.at(diag, b, w)
    diag += 1e-3 * diag.mean()                       # «рекомбинация», чтобы матрица была невырожденной
    rows.append(np.arange(N)); cols.append(np.arange(N)); vals.append(diag)
    A = csp.csr_matrix((cp.asarray(np.concatenate(vals)),
                        (cp.asarray(np.concatenate(rows)), cp.asarray(np.concatenate(cols)))),
                       shape=(N, N))
    A.sum_duplicates()
    return A


def main():
    sizes = [int(s) for s in sys.argv[1:]] or [40, 60, 80]
    free0, total = cp.cuda.runtime.memGetInfo()
    print("GPU: %s, свободно %.1f из %.1f ГБ"
          % (cp.cuda.runtime.getDeviceProperties(0)["name"].decode(), free0 / 2**30, total / 2**30))
    print("%8s %10s %10s %12s %12s" % ("узлов", "solve, с", "повтор, с", "мин. своб., ГБ", "невязка"))
    for n in sizes:
        A = matrix(n)
        x0 = cp.random.default_rng(2).uniform(0.5, 1.5, A.shape[0])
        b = A @ x0
        cp.cuda.Device().synchronize()
        low = [free0]

        t = time.time()
        with nvmath.sparse.advanced.DirectSolver(A, b) as s:
            s.plan(); s.factorize(); x = s.solve()
            cp.cuda.Device().synchronize()
            low.append(cp.cuda.runtime.memGetInfo()[0])
            t1 = time.time() - t
            # повторное разложение с тем же шаблоном — как на каждой итерации Ньютона
            t = time.time()
            s.factorize(); x = s.solve()
            cp.cuda.Device().synchronize()
            t2 = time.time() - t
        res = float(cp.linalg.norm(A @ x - b) / cp.linalg.norm(b))
        err = float(cp.max(cp.abs(x - x0) / x0))
        print("%8d %10.2f %10.2f %12.2f %12.1e  (ош. x %.1e)" % (A.shape[0], t1, t2, min(low) / 2**30, res, err))
        del A, b, x, x0
        cp.get_default_memory_pool().free_all_blocks()


if __name__ == "__main__":
    main()
