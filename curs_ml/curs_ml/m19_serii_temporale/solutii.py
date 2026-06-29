#!/usr/bin/env python3
"""solutii.py -- M19 Serii temporale (SOLUTIILE complete). Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from serii_temporale_core import (  # noqa: E402
    fit_ar, temporal_split, ar_predict_onestep, persistence_forecast, _ar1_process,
)
from date_sar import make_latency_series  # noqa: E402
from utils import rmse  # noqa: E402


def ex1_lag_features(series, p):
    x = np.asarray(series, dtype=float).reshape(-1)
    n = x.size
    X = np.empty((n - p, p))
    for j in range(p):
        X[:, j] = x[p - 1 - j: n - 1 - j]
    return X, x[p:]


def ex2_phi_ar1_de_mana(x4):
    x = np.asarray(x4, dtype=float).reshape(-1)
    x_prev = x[:-1]
    x_curr = x[1:]
    return float(np.sum(x_prev * x_curr) / np.sum(x_prev ** 2))


def ex3_split_fara_lookahead(series, train_frac=0.7):
    _, _, itr, ite = temporal_split(series, train_frac=train_frac)
    return int(itr.max()), int(ite.min())


def ex4_ar_bate_persistenta(series, p=2, train_frac=0.75):
    train, test, _, _ = temporal_split(series, train_frac=train_frac)
    c, phi = fit_ar(train, p=p)
    yt_ar, yp_ar = ar_predict_onestep(test, c, phi, warmup=train)
    yt_pe, yp_pe = persistence_forecast(train, test)
    return float(rmse(yt_ar, yp_ar)), float(rmse(yt_pe, yp_pe))


def ex5_rmse_pe_latenta_mea(cond="loss_15", p=3):
    df = make_latency_series(cond=cond, length=300, seed=4, middleware="DDS")
    series = df["rtt_ms"].to_numpy(dtype=float)
    return ex4_ar_bate_persistenta(series, p=p, train_frac=0.7)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    x = np.arange(8.0)
    X, y = ex1_lag_features(x, 2)
    ck("E1: forma X = (6, 2)", X.shape == (6, 2) and y.shape == (6,))
    ck("E1: primul rand = [x1, x0], tinta x2", np.array_equal(X[0], [1.0, 0.0]) and y[0] == 2.0)

    xa = _ar1_process(2000, phi=0.8, c=0.0, noise=0.2, seed=5)
    ck("E2: phi AR(1) ~ 0.8", abs(ex2_phi_ar1_de_mana(xa) - 0.8) < 0.05)

    mx, mn = ex3_split_fara_lookahead(np.arange(50.0), 0.6)
    ck("E3: max_idx_train < min_idx_test", mx < mn)

    xb = _ar1_process(600, phi=0.8, c=1.0, noise=0.4, seed=6)
    rar, rpe = ex4_ar_bate_persistenta(xb, p=2, train_frac=0.75)
    ck("E4: RMSE_AR < RMSE_persistenta", rar < rpe)

    r_ar, r_pe = ex5_rmse_pe_latenta_mea("loss_15", 3)
    ck("E5: RMSE_AR <= RMSE_persistenta pe latenta", r_ar <= r_pe + 1e-9)

    print("\nTOATE SOLUTIILE M19 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
