#!/usr/bin/env python3
"""solutii.py -- M06 Regularizare (SOLUTIILE complete). Ruleaza cu venv -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from regularizare_core import ridge_fit, ols_fit, lasso_fit  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize  # noqa: E402

FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]


def ex1_ridge_de_mana(X, y, lam):
    X = np.asarray(X, dtype=float); y = np.asarray(y, dtype=float).reshape(-1)
    p = X.shape[1]
    return np.linalg.solve(X.T @ X + lam * np.eye(p), X.T @ y)


def ex2_soft_threshold(z, gamma):
    z = np.asarray(z, dtype=float)
    return np.sign(z) * np.maximum(np.abs(z) - gamma, 0.0)


def ex3_norme_ridge(X, y, lams):
    return [float(np.linalg.norm(ridge_fit(X, y, lam))) for lam in lams]


def ex4_nenule_lasso(X, y, lams):
    return [int(np.sum(np.abs(lasso_fit(X, y, lam, n_iter=1000)) > 1e-6)) for lam in lams]


def ex5_ridge_vs_ols_pe_date():
    df = make_latency_dataset(n_per_cond=120, seed=0)
    X = df[FEATURES].to_numpy(dtype=float)
    y = np.log10(df["rtt_ms"].to_numpy(dtype=float))
    Xs, _, _, _ = standardize(X)
    y = y - y.mean()
    n_ols = float(np.linalg.norm(ols_fit(Xs, y)))
    n_ridge = float(np.linalg.norm(ridge_fit(Xs, y, 10.0)))
    return n_ols, n_ridge


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    rng = np.random.default_rng(0)
    X = rng.standard_normal((50, 4))
    X = (X - X.mean(0)) / X.std(0)
    y = X @ np.array([2.0, 0.0, -1.0, 0.0]) + 0.1 * rng.standard_normal(50)
    y = y - y.mean()

    ck("E1: ridge de mana == ridge_fit", np.allclose(ex1_ridge_de_mana(X, y, 3.0), ridge_fit(X, y, 3.0), atol=1e-9))
    ck("E2: soft_threshold corect",
       abs(float(ex2_soft_threshold(np.array([5.0]), 2.0)[0]) - 3.0) < 1e-12
       and abs(float(ex2_soft_threshold(np.array([-1.0]), 2.0)[0])) < 1e-12)
    norme = ex3_norme_ridge(X, y, [0.1, 1.0, 10.0, 100.0])
    ck("E3: norma Ridge scade cu lam", all(norme[i] > norme[i + 1] for i in range(len(norme) - 1)))
    nz = ex4_nenule_lasso(X, y, [0.5, 5.0, 30.0])
    ck("E4: nenule Lasso scad cu lam", nz[0] >= nz[1] >= nz[2] and nz[-1] < nz[0])
    n_ols, n_ridge = ex5_ridge_vs_ols_pe_date()
    ck("E5: norma Ridge < norma OLS", n_ridge < n_ols)

    print("\nTOATE SOLUTIILE M06 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
