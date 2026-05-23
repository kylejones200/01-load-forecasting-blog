#!/usr/bin/env python3
"""Python vs Rust — SAIDI/SAIFI flat-array benchmark."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from compute_kernel import saidi_saifi_by_key  # noqa: E402

MODULE = "load_forecasting_blog_rs"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=100_000)
    p.add_argument("--iterations", type=int, default=2_000)
    args = p.parse_args()
    n = args.n
    g = np.arange(n, dtype=np.int64) % 50
    co = (np.arange(n) % 7).astype(float)
    sm = np.full(n, 15.0)
    cs = np.full(n, 1000.0)

    t0 = time.perf_counter()
    for _ in range(args.iterations):
        saidi_saifi_by_key(g, co, sm, cs)
    py_s = time.perf_counter() - t0

    try:
        import load_forecasting_blog_rs as rs  # noqa: F401
    except ImportError:
        print(f"Rust extension not built. cd rust && maturin develop --release -m py/Cargo.toml")
        print(f"Python: {py_s:.3f}s")
        return

    rs_s = rs.bench_kernel_py(g, co, sm, cs, args.iterations)
    print(f"Python: {py_s:.3f}s  Rust: {rs_s:.3f}s  speedup: {py_s / rs_s:.1f}x")
    py_out = saidi_saifi_by_key(g[:500], co[:500], sm[:500], cs[:500])
    rs_out = rs.saidi_saifi_by_key_py(g[:500], co[:500], sm[:500], cs[:500])
    for a, b in zip(py_out, rs_out):
        np.testing.assert_allclose(a, np.asarray(b), rtol=1e-10)
    print("Correctness: OK")


if __name__ == "__main__":
    main()
