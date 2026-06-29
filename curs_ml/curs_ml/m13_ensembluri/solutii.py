#!/usr/bin/env python3
"""solutii.py -- M13 Ensembluri (SOLUTIILE complete). Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from ensembluri_core import (  # noqa: E402
    DecisionStump, BaggingClassifier, GradientBoostingClassifier, _sigmoid, _toy_noisy,
)
from date_sar import make_mission_outcome_dataset  # noqa: E402
from utils import accuracy  # noqa: E402

FEATURES = ["delivered_frac", "p95_ms", "n_drones"]


def ex1_bootstrap_indices(n, seed):
    return np.random.default_rng(seed).integers(0, n, size=n)


def ex2_oob_fraction(n=2000, seed=0):
    idx = ex1_bootstrap_indices(n, seed)
    inside = np.unique(idx)
    n_oob = n - inside.size
    return float(n_oob) / float(n)


def ex3_bagging_bate_ciotul(seed=0):
    Xtr, ytr = _toy_noisy(n=400, seed=11)
    Xte, yte = _toy_noisy(n=400, seed=22)
    ciot = DecisionStump(task="clf").fit(Xtr, ytr)
    bag = BaggingClassifier(n_estimators=41, seed=seed).fit(Xtr, ytr)
    acc_ciot = accuracy(yte, ciot.predict(Xte).astype(int))
    acc_bag = accuracy(yte, bag.predict(Xte))
    return float(acc_ciot), float(acc_bag)


def ex4_un_pas_boosting(y, p, residual_pred, lr):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    residual = y - p
    delta_F = lr * np.asarray(residual_pred, dtype=float)
    return residual, delta_F


def ex5_supra_invatare_boosting():
    df = make_mission_outcome_dataset(n=600, seed=3)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["mission_complete"].to_numpy(dtype=int)
    perm = np.random.default_rng(0).permutation(len(y))
    cut = int(0.75 * len(y))
    tr, te = perm[:cut], perm[cut:]
    gb = GradientBoostingClassifier(n_estimators=300, learning_rate=0.5).fit(X[tr], y[tr])
    F_stages = gb.staged_decision_function(X[te])
    err120 = 1.0 - accuracy(y[te], (_sigmoid(F_stages[119]) >= 0.5).astype(int))
    err300 = 1.0 - accuracy(y[te], (_sigmoid(F_stages[299]) >= 0.5).astype(int))
    return float(err120), float(err300)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    idx = ex1_bootstrap_indices(50, seed=0)
    ck("E1: 50 indici in 0..49 cu repetitii",
       len(idx) == 50 and idx.min() >= 0 and idx.max() <= 49 and len(set(idx.tolist())) < 50)
    ck("E1: determinist", np.array_equal(idx, ex1_bootstrap_indices(50, seed=0)))

    oob = ex2_oob_fraction(n=3000, seed=1)
    ck("E2: out-of-bag ~ 1/e", abs(oob - 1.0 / np.e) < 0.03)

    acc_ciot, acc_bag = ex3_bagging_bate_ciotul()
    ck("E3: bagging >= ciot", acc_bag >= acc_ciot - 1e-9)

    y = np.array([1.0, 0.0, 1.0, 0.0])
    p = np.array([0.6, 0.3, 0.4, 0.5])
    rp = np.array([0.4, -0.3, 0.6, -0.5])
    residual, dF = ex4_un_pas_boosting(y, p, rp, lr=0.5)
    ck("E4: reziduul = y - p", np.allclose(residual, y - p))
    ck("E4: delta_F = lr * residual_pred", np.allclose(dF, 0.5 * rp))

    e120, e300 = ex5_supra_invatare_boosting()
    ck("E5: pasii in plus nu mai imbunatatesc testul (plateau)", e300 >= e120 - 0.01)

    print("\nTOATE SOLUTIILE M13 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
