#!/usr/bin/env python3
"""solutii.py -- M14 Interpretabilitate (SOLUTIILE complete). Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from interpretabilitate_core import (  # noqa: E402
    permutation_importance, partial_dependence, shapley_linear,
    _linfit, _make_predict,
)
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import standardize, r2_score  # noqa: E402

FEATURES = ["p95_ms", "loss_frac", "jitter_ms", "base_lat_ms", "mw_zenoh", "distance_m"]


def ex1_shapley_manual(w, x, x_mean):
    w = np.asarray(w, dtype=float)
    x = np.asarray(x, dtype=float)
    x_mean = np.asarray(x_mean, dtype=float)
    return w * (x - x_mean)


def ex2_eficienta(w, x, x_mean, w0):
    w = np.asarray(w, dtype=float)
    x = np.asarray(x, dtype=float)
    x_mean = np.asarray(x_mean, dtype=float)
    phi = shapley_linear(w, x, x_mean)
    fx = float(w0 + w @ x)
    baza = float(w0 + w @ x_mean)
    return float(phi.sum()), fx - baza


def ex3_pdp_panta(coef):
    coef = np.asarray(coef, dtype=float)
    pred = _make_predict(0.0, coef)
    X = np.random.default_rng(0).uniform(-1, 1, size=(200, coef.size))
    grid = np.linspace(-3, 3, 7)
    pdp = partial_dependence(pred, X, feature_idx=0, grid=grid)
    return float((pdp[-1] - pdp[0]) / (grid[-1] - grid[0]))


def ex4_importanta_zgomot():
    g = np.random.default_rng(0)
    n = 400
    x0 = g.uniform(-2, 2, size=n)
    x1 = g.uniform(-2, 2, size=n)
    X = np.column_stack([x0, x1])
    y = 3.0 * x0 + 0.5 + 0.01 * g.standard_normal(n)
    w0, w = _linfit(X, y)
    pred = _make_predict(w0, w)
    imp = permutation_importance(pred, X, y, metric=r2_score, n_repeats=20, seed=1)
    return float(imp[0]), float(imp[1])


def ex5_top_feature_link():
    df = make_link_usability_dataset(n_per_cond=200, seed=1)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["usable"].to_numpy(dtype=float)
    Xs, _, _, _ = standardize(X)
    w0, w = _linfit(Xs, y)
    pred = _make_predict(w0, w)
    imp = permutation_importance(pred, Xs, y, metric=r2_score, n_repeats=30, seed=2)
    return FEATURES[int(np.argmax(imp))]


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    phi = ex1_shapley_manual([2.0, -3.0], [1.0, 4.0], [0.0, 5.0])
    ck("E1: phi = [2, 3]", np.allclose(phi, [2.0, 3.0]))
    s, d = ex2_eficienta([1.5, -2.0, 0.7], [0.3, -0.4, 1.1], [0.0, 0.0, 0.0], 0.4)
    ck("E2: suma(phi) = f(x) - baza", abs(s - d) < 1e-12)
    ck("E3: panta PDP pe feature 0 ~ 2.0", abs(ex3_pdp_panta([2.0, -1.0]) - 2.0) < 1e-9)
    i0, i1 = ex4_importanta_zgomot()
    ck("E4: feature 0 important (> 0.5)", i0 > 0.5)
    ck("E4: feature de zgomot ~0 (< 0.02)", abs(i1) < 0.02)
    ck("E5: top feature de link este p95_ms", ex5_top_feature_link() == "p95_ms")

    print("\nTOATE SOLUTIILE M14 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
