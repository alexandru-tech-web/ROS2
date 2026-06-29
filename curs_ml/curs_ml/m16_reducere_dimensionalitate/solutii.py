#!/usr/bin/env python3
"""solutii.py -- M16 Reducerea dimensionalitatii / PCA (SOLUTIILE complete).
Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from pca_core import PCA, _dominant_direction_data  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize  # noqa: E402

FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]


def ex1_centre_cov(X):
    X = np.asarray(X, dtype=float)
    Xc = X - X.mean(axis=0)
    n = X.shape[0]
    C = (Xc.T @ Xc) / (n - 1)
    return Xc, C


def ex2_var_dir(X, w):
    w = np.asarray(w, dtype=float)
    _, C = ex1_centre_cov(X)
    return float(w @ C @ w)


def ex3_n_componente(ratii, prag):
    cum = np.cumsum(np.asarray(ratii, dtype=float))
    return int(np.searchsorted(cum, prag - 1e-12) + 1)


def ex4_pc1_dominanta(seed=1):
    X, u_true = _dominant_direction_data(n=400, seed=seed)
    p = PCA().fit(X)
    ratie = float(p.explained_variance_ratio_[0])
    cos = abs(float(p.components_[0] @ u_true))
    return ratie, cos


def ex5_var_2d():
    df = make_latency_dataset(n_per_cond=150, seed=0)
    X = df[FEATURES].to_numpy(dtype=float)
    Xs, _, _, _ = standardize(X)
    p = PCA().fit(Xs)
    return float(p.explained_variance_ratio_[:2].sum())


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    X4 = np.array([[2.0, 0.0], [0.0, 2.0], [-2.0, 0.0], [0.0, -2.0]])
    Xc, C = ex1_centre_cov(X4)
    ck("E1: media centrata e zero", np.allclose(Xc.mean(axis=0), 0.0))
    ck("E1: C == [[8/3,0],[0,8/3]]", np.allclose(C, [[8 / 3, 0], [0, 8 / 3]]))

    Xd = np.array([[2.0, 0.0], [0.0, 6.0], [-2.0, 0.0], [0.0, -6.0]])
    ck("E2: varianta pe (0,1) = 24", abs(ex2_var_dir(Xd, np.array([0.0, 1.0])) - 24.0) < 1e-9)
    ck("E2: varianta pe (1,0) = 8/3", abs(ex2_var_dir(Xd, np.array([1.0, 0.0])) - 8 / 3) < 1e-9)

    ck("E3: 3 componente pentru prag 0.9", ex3_n_componente([0.6, 0.25, 0.1, 0.05], 0.9) == 3)

    ratie, cos = ex4_pc1_dominanta(seed=1)
    ck("E4: PC1 capteaza > 80% varianta", ratie > 0.8)
    ck("E4: PC1 aliniata cu directia (|cos| > 0.99)", cos > 0.99)

    v2 = ex5_var_2d()
    ck("E5: varianta cumulata 2D in (0,1]", 0.0 < v2 <= 1.0)

    print("\nTOATE SOLUTIILE M16 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
