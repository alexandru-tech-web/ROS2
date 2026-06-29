#!/usr/bin/env python3
"""solutii.py -- M07 Evaluare si validare (SOLUTIILE complete). Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from evaluare_validare_core import (  # noqa: E402
    cross_val_score, learning_curve, _ols_fit_predict,
)
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize  # noqa: E402

FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]


def ex1_kfold_manual(n, k):
    return [np.sort(b) for b in np.array_split(np.arange(n), k)]


def ex2_rmse_mae(y_true, y_pred):
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(np.mean((yt - yp) ** 2)))
    mae = float(np.mean(np.abs(yt - yp)))
    return rmse, mae


def ex3_k_pentru_loocv(n):
    return int(n)


def ex4_cv_mean_rmse(X, y, k=5, seed=0):
    return float(cross_val_score(X, y, _ols_fit_predict, k=k, seed=seed).mean())


def ex5_gol_invatare():
    df = make_latency_dataset(n_per_cond=150, seed=0)
    X = df[FEATURES].to_numpy(dtype=float)
    y = np.log10(df["rtt_ms"].to_numpy(dtype=float))
    Xs, _, _, _ = standardize(X)
    _, va = learning_curve(Xs, y, _ols_fit_predict, train_sizes=[10, 600], seed=0)
    return float(va[0]), float(va[1])


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    folds = ex1_kfold_manual(10, 3)
    allt = np.concatenate(folds)
    ck("E1: 3 falduri acopera 0..9", len(folds) == 3 and sorted(allt.tolist()) == list(range(10)))
    r, m = ex2_rmse_mae([1.0, 2.0, 3.0], [1.0, 4.0, 3.0])
    ck("E2: rmse = sqrt(4/3)", abs(r - np.sqrt(4.0 / 3.0)) < 1e-12)
    ck("E2: mae = 2/3", abs(m - 2.0 / 3.0) < 1e-12)
    ck("E3: k LOOCV pe n=7 = 7", ex3_k_pentru_loocv(7) == 7)
    rng = np.random.default_rng(0)
    X = rng.uniform(-2, 2, (120, 3))
    y = X @ np.array([1.0, -1.0, 0.5]) + 0.05 * rng.standard_normal(120)
    ck("E4: media RMSE CV < 0.2", ex4_cv_mean_rmse(X, y, 5, 0) < 0.2)
    vm, vM = ex5_gol_invatare()
    ck("E5: validare set mare <= set mic", vM <= vm + 1e-9)

    print("\nTOATE SOLUTIILE M07 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
