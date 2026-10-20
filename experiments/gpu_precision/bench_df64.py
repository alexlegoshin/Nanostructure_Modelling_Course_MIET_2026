# -*- coding: utf-8 -*-
"""Замер на TITAN X Pascal: FP64 против df64 (пара float32) против FP32.

Два ядра, как в будущем решателе на тензорной сетке:
  stencil — 7-точечный шаблон с коэффициентами на узел (y = A·x), упор в память;
  chain   — 256 FMA подряд на элемент, упор в арифметику (как сборка потоков).
df64 — число как hi+lo в float32 (Деккер/Кнут: two_sum, two_prod через fmaf),
~48 бит мантиссы против 53 у double, порядок как у float32.

    python bench_df64.py [n]      # сетка n^3, по умолчанию 200 (8 млн узлов)
"""
import sys
import numpy as np
import cupy as cp

DF64 = r"""
struct df { float hi, lo; };
__device__ __forceinline__ df two_sum(float a, float b) {
    float s = a + b, bb = s - a; return { s, (a - (s - bb)) + (b - bb) };
}
__device__ __forceinline__ df fast_two_sum(float a, float b) {
    float s = a + b; return { s, b - (s - a) };
}
__device__ __forceinline__ df df_add(df a, df b) {
    df s = two_sum(a.hi, b.hi), t = two_sum(a.lo, b.lo);
    s.lo += t.hi; s = fast_two_sum(s.hi, s.lo);
    s.lo += t.lo; return fast_two_sum(s.hi, s.lo);
}
__device__ __forceinline__ df df_mul(df a, df b) {
    float p = a.hi * b.hi, e = fmaf(a.hi, b.hi, -p);
    e = fmaf(a.hi, b.lo, fmaf(a.lo, b.hi, e));
    return fast_two_sum(p, e);
}
__device__ __forceinline__ df df_fma(df a, df b, df c) { return df_add(df_mul(a, b), c); }
"""

KERNELS = r"""
#define IDX(i,j,k) (((i)*ny + (j))*nz + (k))
extern "C" __global__ void st_T(const T* __restrict__ x, const T* __restrict__ c, T* __restrict__ y,
                               int nx, int ny, int nz) {
    long n = (long)nx*ny*nz, id = (long)blockIdx.x*blockDim.x + threadIdx.x;
    if (id >= n) return;
    int k = id % nz, j = (id / nz) % ny, i = id / ((long)ny*nz);
    if (i == 0 || j == 0 || k == 0 || i == nx-1 || j == ny-1 || k == nz-1) { y[id] = x[id]; return; }
    long nb[6] = { IDX(i-1,j,k), IDX(i+1,j,k), IDX(i,j-1,k), IDX(i,j+1,k), IDX(i,j,k-1), IDX(i,j,k+1) };
    ACC s = MUL(LOAD(c[id]), LOAD(x[id]));
    #pragma unroll
    for (int m = 0; m < 6; ++m) s = MADD(LOAD(c[(m+1)*n + id]), LOAD(x[nb[m]]), s);
    y[id] = STORE(s);
}
extern "C" __global__ void ch_T(const T* __restrict__ x, T* __restrict__ y, long n) {
    long id = (long)blockIdx.x*blockDim.x + threadIdx.x;
    if (id >= n) return;
    ACC a = LOAD(x[id]), s = a, b = ONEM;
    #pragma unroll 16
    for (int r = 0; r < 256; ++r) s = MADD(s, b, a);
    y[id] = STORE(s);
}
"""

PLAIN = "#define LOAD(z) (z)\n#define STORE(z) (z)\n#define MUL(a,b) ((a)*(b))\n"
VARIANTS = {
    "fp64": "#define T double\n#define ACC double\n#define MADD fma\n#define ONEM 0.75\n" + PLAIN,
    "fp32": "#define T float\n#define ACC float\n#define MADD fmaf\n#define ONEM 0.75f\n" + PLAIN,
    "df64": "#define T float2\n#define ACC df\n#define MADD df_fma\n#define ONEM (df{0.75f, 0.0f})\n"
            "#define LOAD(z) TOD(z)\n#define STORE(z) TOF2(z)\n#define MUL(a,b) df_mul(a,b)\n",
}
CONV = r"""
__device__ __forceinline__ df TOD(float2 v) { return { v.x, v.y }; }
__device__ __forceinline__ float2 TOF2(df v) { return make_float2(v.hi, v.lo); }
"""


def build(name):
    src = VARIANTS[name] + DF64 + CONV + KERNELS
    mod = cp.RawModule(code=src)        # без --use_fast_math: df64 держится на точных a+b и fmaf
    return mod.get_function("st_T"), mod.get_function("ch_T")


def to_dev(a, name):
    if name == "fp64":
        return cp.asarray(a, dtype=cp.float64)
    if name == "fp32":
        return cp.asarray(a, dtype=cp.float32)
    hi = a.astype(np.float32)
    lo = (a - hi.astype(np.float64)).astype(np.float32)
    return cp.asarray(np.stack([hi, lo], axis=-1))          # float2 = (hi, lo) подряд


def from_dev(d, name):
    h = cp.asnumpy(d)
    return h[..., 0].astype(np.float64) + h[..., 1].astype(np.float64) if name == "df64" else h.astype(np.float64)


def timeit(fn, reps=20):
    fn(); cp.cuda.Device().synchronize()
    e0, e1 = cp.cuda.Event(), cp.cuda.Event()
    e0.record()
    for _ in range(reps):
        fn()
    e1.record(); e1.synchronize()
    return cp.cuda.get_elapsed_time(e0, e1) / reps / 1e3


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    N = n ** 3
    rng = np.random.default_rng(1)
    x = rng.uniform(0.5, 1.5, N)
    c = rng.uniform(-1.0, 1.0, 7 * N); c[:N] = 6.5             # диагональное преобладание
    bs = 256
    grid = ((N + bs - 1) // bs,)
    ref = {}
    print("сетка %d^3 = %.1f млн узлов, %s" % (n, N / 1e6, cp.cuda.runtime.getDeviceProperties(0)["name"].decode()))
    print("%-5s %12s %10s %14s %14s" % ("", "stencil, мс", "ГБ/с", "chain, мс", "Гфлоп/с*"))
    for name in ("fp64", "df64", "fp32"):
        st, ch = build(name)
        xd, cd = to_dev(x, name), to_dev(c, name)
        yd = cp.empty_like(xd)
        t_st = timeit(lambda: st(grid, (bs,), (xd, cd, yd, np.int32(n), np.int32(n), np.int32(n))))
        ys = from_dev(yd, name)
        t_ch = timeit(lambda: ch(grid, (bs,), (xd, yd, np.int64(N))), reps=5)
        yc = from_dev(yd, name)
        word = 4 if name == "fp32" else 8
        gbs = (8 + 1) * N * word / t_st / 1e9                  # 7 коэфф. + x + y, без повторных чтений x
        gfl = 2 * 256 * N / t_ch / 1e9                         # «полезных» флопов, 1 FMA = 2
        print("%-5s %12.2f %10.0f %14.2f %14.0f" % (name, t_st * 1e3, gbs, t_ch * 1e3, gfl))
        if name == "fp64":
            ref = {"st": ys, "ch": yc}
        else:
            for k, y in (("stencil", ys), ("chain", yc)):
                r = ref["st" if k == "stencil" else "ch"]
                err = np.max(np.abs(y - r) / np.maximum(np.abs(r), 1e-30))
                print("      %s: макс. отн. отличие от fp64 = %.1e" % (k, err))
        del xd, cd, yd
        cp.get_default_memory_pool().free_all_blocks()
    print("* для df64 — эквивалентных флопов двойной точности")


if __name__ == "__main__":
    main()
