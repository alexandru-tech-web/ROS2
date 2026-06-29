#!/usr/bin/env python3
"""solutii.py -- solutiile complete pentru exercitii.py (M04).

Rulat cu venv trebuie sa TREACA (iesire 0):
  /home/ubuntu/ros2_ws/.venv_ml/bin/python solutii.py

Foloseste acelasi set de verificari ca exercitii.py, dar cu functiile rezolvate.
Refoloseste nucleul din date_features_core (DRY).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from date_features_core import (  # noqa: E402
    fit_one_hot, transform_one_hot,
    fit_mean_imputer, transform_mean_imputer,
    polynomial_features, iqr_outlier_mask, n_polynomial_features,
)
from date_sar import make_latency_dataset  # noqa: E402
from utils import train_test_split, standardize  # noqa: E402


# --------------------------------------------------------------------------
# Ex.1 -- one-hot manual.
def ex1_one_hot(labels):
    cats = fit_one_hot(labels)            # vocabular sortat
    return transform_one_hot(labels, cats)


# --------------------------------------------------------------------------
# Ex.2 -- imputare FARA scurgere (media de pe TRAIN aplicata pe ambele seturi).
def ex2_impute_no_leak(Xtr, Xte):
    means = fit_mean_imputer(Xtr)         # invata DOAR pe TRAIN
    return transform_mean_imputer(Xtr, means), transform_mean_imputer(Xte, means)


# --------------------------------------------------------------------------
# Ex.3 -- numarul de coloane polinomiale (fara bias).
def ex3_n_poly_cols(p, degree):
    return n_polynomial_features(p, degree=degree, include_bias=False)


# --------------------------------------------------------------------------
# Ex.4 -- fractia de outlieri IQR pe rtt_ms.
def ex4_outlier_fraction():
    df = make_latency_dataset(n_per_cond=200, seed=0)
    mask = iqr_outlier_mask(df["rtt_ms"].to_numpy(), k=1.5)
    return float(mask.mean())


# --------------------------------------------------------------------------
# Ex.5 -- pipeline mic fara scurgere (one-hot + z-score).
def ex5_pipeline(df):
    mid = df["middleware"].to_numpy()
    num = df[["loss_pct", "distance_m"]].to_numpy(dtype=float)
    n = len(df)
    idx = np.arange(n)
    idx_tr, idx_te, _, _ = train_test_split(idx.reshape(-1, 1), idx, test_frac=0.25, seed=0)
    itr, ite = idx_tr.ravel().astype(int), idx_te.ravel().astype(int)

    cats = fit_one_hot(mid[itr])          # vocabular de pe TRAIN
    oh_tr = transform_one_hot(mid[itr], cats)
    oh_te = transform_one_hot(mid[ite], cats)

    num_tr_s, num_te_s, _, _ = standardize(num[itr], num[ite])  # stat de pe TRAIN

    F_tr = np.column_stack([oh_tr, num_tr_s])
    F_te = np.column_stack([oh_te, num_te_s])
    return F_tr, F_te


# ==========================================================================
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # ex1
    M = ex1_one_hot(["b", "a", "c", "a"])
    ck("ex1: forma (4,3)", np.shape(M) == (4, 3))
    ck("ex1: un singur 1 per rand", np.array_equal(np.sum(M, axis=1), np.ones(4)))
    ck("ex1: rand 0 ('b') aprinde coloana 1", M[0, 1] == 1.0)

    # ex2
    Xtr = np.array([[1.0, 10.0], [3.0, np.nan], [np.nan, 20.0]])
    Xte = np.array([[np.nan, np.nan]])
    Atr, Ate = ex2_impute_no_leak(Xtr, Xte)
    ck("ex2: fara NaN dupa imputare", not np.isnan(Atr).any() and not np.isnan(Ate).any())
    ck("ex2: media TRAIN col0 = 2.0", abs(Atr[2, 0] - 2.0) < 1e-9)
    ck("ex2: TEST umplut cu media TRAIN (col0=2.0)", abs(Ate[0, 0] - 2.0) < 1e-9)

    # ex3
    ck("ex3: p=4,degree=2 -> 14", ex3_n_poly_cols(4, 2) == 14)
    ck("ex3: p=2,degree=3 -> 9", ex3_n_poly_cols(2, 3) == 9)

    # ex4
    frac = ex4_outlier_fraction()
    ck("ex4: fractie outlieri in (0, 0.5)", 0.0 < frac < 0.5)

    # ex5
    df = make_latency_dataset(n_per_cond=50, seed=0)
    F_tr, F_te = ex5_pipeline(df)
    ck("ex5: 4 coloane (2 one-hot + 2 z)", F_tr.shape[1] == 4)
    ck("ex5: train+test = tot setul", F_tr.shape[0] + F_te.shape[0] == len(df))
    ck("ex5: media z pe TRAIN ~ 0", np.allclose(F_tr[:, 2:].mean(axis=0), 0, atol=1e-9))

    print("\nTOATE SOLUTIILE M04 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
