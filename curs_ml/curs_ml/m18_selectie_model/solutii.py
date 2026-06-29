#!/usr/bin/env python3
"""solutii.py -- M18 Selectie de model si reglare hiperparametri (SOLUTIILE complete).
Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # .../m18_selectie_model

from selectie_model_core import (  # noqa: E402
    grid_search_cv, nested_cv, _poly_design, gaussian_neg2ll, aic, bic,
)
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize  # noqa: E402


def _fit_predict_poly_1d(X_tr, y_tr, X_te, deg):
    x_tr = np.asarray(X_tr, dtype=float)[:, 0]
    x_te = np.asarray(X_te, dtype=float)[:, 0]
    Phi = _poly_design(x_tr, deg)
    w, *_ = np.linalg.lstsq(Phi, y_tr, rcond=None)
    return _poly_design(x_te, deg) @ w


def ex1_alege_grad(x, y, grid, k=5, seed=0):
    X = np.asarray(x, dtype=float).reshape(-1, 1)
    best, _, _ = grid_search_cv(X, y, _fit_predict_poly_1d, grid, k=k, seed=seed)
    return int(best)


def ex2_aic(neg2ll, k):
    return 2.0 * k + float(neg2ll)


def ex3_alege_model(rss_a, k_a, rss_b, k_b, n, criteriu="aic"):
    n2ll_a = gaussian_neg2ll(rss_a, n)
    n2ll_b = gaussian_neg2ll(rss_b, n)
    if criteriu == "aic":
        va, vb = aic(n2ll_a, k_a), aic(n2ll_b, k_b)
    elif criteriu == "bic":
        va, vb = bic(n2ll_a, k_a, n), bic(n2ll_b, k_b, n)
    else:
        raise ValueError("criteriu necunoscut: %r (aic|bic)" % (criteriu,))
    return "A" if va <= vb else "B"


def ex4_penalizare_pe_parametru(n):
    return 2.0, float(np.log(n))


def ex5_eroare_onesta():
    df = make_latency_dataset(n_per_cond=120, seed=0)
    x = df["distance_m"].to_numpy(dtype=float).reshape(-1, 1)
    y = np.log10(df["rtt_ms"].to_numpy(dtype=float))
    Xs, _, _, _ = standardize(x)
    grid = [1, 2, 3, 4, 5, 6]
    _, sel, _ = grid_search_cv(Xs, y, _fit_predict_poly_1d, grid, k=5, seed=0)
    onest, _, _ = nested_cv(Xs, y, _fit_predict_poly_1d, grid,
                            k_outer=5, k_inner=4, seed=0)
    return float(sel), float(onest)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    g = np.random.default_rng(0)
    x = g.uniform(-2, 2, 80)
    y = 0.5 * x ** 3 - x + 1.0 + 0.3 * g.standard_normal(80)
    ck("E1: grid search alege gradul 3", ex1_alege_grad(x, y, [1, 2, 3, 4, 5], 5, 0) == 3)

    ck("E2: AIC(-2lnL=218, k=3) = 224", abs(ex2_aic(218.0, 3) - 224.0) < 1e-9)

    ck("E3 (AIC): A castiga", ex3_alege_model(52.0, 3, 50.0, 6, 100, "aic") == "A")
    ck("E3 (BIC): A castiga", ex3_alege_model(52.0, 3, 50.0, 6, 100, "bic") == "A")

    pa, pb = ex4_penalizare_pe_parametru(100)
    ck("E4: penalizarea AIC = 2", abs(pa - 2.0) < 1e-12)
    ck("E4: BIC penalizeaza mai tare ca AIC la n=100", pb > pa)

    sel, onest = ex5_eroare_onesta()
    ck("E5: nested >= selectie", onest >= sel - 1e-9)

    print("\nTOATE SOLUTIILE M18 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
