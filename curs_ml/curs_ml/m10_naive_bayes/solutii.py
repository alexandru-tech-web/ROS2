#!/usr/bin/env python3
"""solutii.py -- M10 Naive Bayes (SOLUTIILE complete). Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from naive_bayes_core import GaussianNaiveBayes  # noqa: E402
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import train_test_split, standardize, accuracy  # noqa: E402

FEATURES = ["p95_ms", "loss_frac", "jitter_ms", "distance_m", "mw_zenoh"]


def ex1_log_gaussian(x, mu, var):
    return float(-0.5 * np.log(2.0 * np.pi * var) - (x - mu) ** 2 / (2.0 * var))


def ex2_estimari(X, y):
    X = np.asarray(X, dtype=float).reshape(-1)
    y = np.asarray(y)
    xc = X[y == 1]
    prior = xc.size / y.size
    return float(prior), float(xc.mean()), float(xc.var())


def ex3_log_posterior(x):
    Xs = np.array([[1.0], [2.0], [3.0], [5.0], [6.0], [7.0]])
    ys = np.array([0, 0, 0, 1, 1, 1])
    m = GaussianNaiveBayes(var_smoothing=0.0).fit(Xs, ys)
    return m.predict_log_proba(np.array([[float(x)]]))[0]


def ex4_prior_dominant():
    rng = np.random.default_rng(0)
    Xa = rng.normal(0.0, 1.0, size=(90, 1))
    Xb = rng.normal(0.0, 1.0, size=(10, 1))
    X = np.vstack([Xa, Xb])
    y = np.r_[np.zeros(90), np.ones(10)].astype(int)
    m = GaussianNaiveBayes().fit(X, y)
    return int(m.predict(np.array([[0.0]]))[0])


def ex5_nb_vs_baza():
    df = make_link_usability_dataset(n_per_cond=120, seed=1)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["usable"].to_numpy(dtype=int)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_frac=0.25, seed=0)
    X_tr_s, X_te_s, _, _ = standardize(X_tr, X_te)
    clf = GaussianNaiveBayes().fit(X_tr_s, y_tr)
    acc_nb = accuracy(y_te, clf.predict(X_te_s))
    maj = int(np.bincount(y_tr).argmax())
    acc_maj = accuracy(y_te, np.full_like(y_te, maj))
    return float(acc_nb), float(acc_maj)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    val = ex1_log_gaussian(0.0, 0.0, 1.0)
    ck("E1: log N(0;0,1) = -0.5*log(2*pi)", abs(val + 0.5 * np.log(2 * np.pi)) < 1e-12)

    X = np.array([[1.0], [2.0], [3.0], [5.0], [6.0], [7.0]])
    y = np.array([0, 0, 0, 1, 1, 1])
    pr, mu, var = ex2_estimari(X, y)
    ck("E2: prior clasa 1 = 0.5", abs(pr - 0.5) < 1e-12)
    ck("E2: mu clasa 1 = 6", abs(mu - 6.0) < 1e-12)
    ck("E2: var clasa 1 = 2/3", abs(var - 2.0 / 3.0) < 1e-12)

    v = 2.0 / 3.0
    lp0 = np.log(0.5) - 0.5 * np.log(2 * np.pi * v) - (3 - 2.0) ** 2 / (2 * v)
    lp1 = np.log(0.5) - 0.5 * np.log(2 * np.pi * v) - (3 - 6.0) ** 2 / (2 * v)
    got = ex3_log_posterior(3.0)
    ck("E3: log-posterior x=3 == manual", np.allclose(got, [lp0, lp1]))

    ck("E4: prezice clasa cu prior dominant (0)", ex4_prior_dominant() == 0)

    acc_nb, acc_maj = ex5_nb_vs_baza()
    ck("E5: NB bate baza triviala", acc_nb > acc_maj)

    print("\nTOATE SOLUTIILE M10 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
