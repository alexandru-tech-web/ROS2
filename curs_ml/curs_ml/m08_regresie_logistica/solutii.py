#!/usr/bin/env python3
"""solutii.py -- M08 Regresie logistica (SOLUTIILE complete). Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from regresie_logistica_core import (  # noqa: E402
    sigmoid, cross_entropy_loss, LogisticRegressionGD,
)
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import standardize, add_bias, precision_recall_f1  # noqa: E402

FEATURES = ["p95_ms", "loss_frac", "jitter_ms", "distance_m", "mw_zenoh"]


def ex1_sigmoid_proprietati(z):
    s = sigmoid(z)
    return float(s), float(1.0 - sigmoid(-z))


def ex2_log_loss_manual(y_true, p):
    yt = np.asarray(y_true, dtype=float).reshape(-1)
    pp = np.clip(np.asarray(p, dtype=float).reshape(-1), 1e-12, 1 - 1e-12)
    return float(-np.mean(yt * np.log(pp) + (1.0 - yt) * np.log(1.0 - pp)))


def ex3_un_pas_gradient(X, y, w, lr):
    Phi = add_bias(X)
    yy = np.asarray(y, dtype=float).reshape(-1)
    p = sigmoid(Phi @ w)
    g = (Phi.T @ (p - yy)) / Phi.shape[0]
    return w - lr * g


def ex4_acuratete_test(seed=0):
    df = make_link_usability_dataset(n_per_cond=120, seed=1)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["usable"].to_numpy(dtype=int)
    Xs, _, _, _ = standardize(X)
    model = LogisticRegressionGD(lr=0.3, n_iter=4000, seed=seed).fit(Xs, y)
    return float(np.mean(model.predict(Xs) == y))


def ex5_prag_si_recall(prag):
    df = make_link_usability_dataset(n_per_cond=120, seed=1)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["usable"].to_numpy(dtype=int)
    Xs, _, _, _ = standardize(X)
    model = LogisticRegressionGD(lr=0.3, n_iter=4000, seed=0).fit(Xs, y)
    pred = model.predict(Xs, threshold=prag)
    _, rec, _ = precision_recall_f1(y, pred)
    return float(rec)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    s, comp = ex1_sigmoid_proprietati(0.0)
    ck("E1: sigmoid(0) = 0.5", abs(s - 0.5) < 1e-12)
    s2, comp2 = ex1_sigmoid_proprietati(1.7)
    ck("E1: sigmoid(z) = 1 - sigmoid(-z)", abs(s2 - comp2) < 1e-12)

    # log-loss: o predictie perfecta -> ~0; o predictie 0.5 peste tot -> log 2
    ck("E2: log-loss predictie perfecta ~ 0",
       ex2_log_loss_manual([1, 0, 1], [1 - 1e-9, 1e-9, 1 - 1e-9]) < 1e-6)
    ck("E2: log-loss la p=0.5 = ln 2",
       abs(ex2_log_loss_manual([1, 0], [0.5, 0.5]) - np.log(2.0)) < 1e-9)

    # un pas de gradient scade pierderea
    rng = np.random.default_rng(0)
    X = rng.standard_normal((50, 2))
    y = (X[:, 0] + X[:, 1] > 0).astype(int)
    w0 = np.zeros(3)
    w1 = ex3_un_pas_gradient(X, y, w0, lr=0.5)
    l0 = cross_entropy_loss(y, sigmoid(add_bias(X) @ w0))
    l1 = cross_entropy_loss(y, sigmoid(add_bias(X) @ w1))
    ck("E3: un pas de gradient scade pierderea", l1 < l0)

    ck("E4: acuratete pe train > 0.9", ex4_acuratete_test() > 0.9)

    r_lo = ex5_prag_si_recall(0.1)
    r_hi = ex5_prag_si_recall(0.9)
    ck("E5: prag mai mic -> recall >= prag mai mare", r_lo >= r_hi - 1e-9)

    print("\nTOATE SOLUTIILE M08 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
