#!/usr/bin/env python3
"""solutii.py -- M17 Cuantificarea incertitudinii (SOLUTIILE complete). Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from incertitudine_core import (  # noqa: E402
    BayesianLinearRegression, bootstrap_predict_interval, conformal_split,
    empirical_coverage, _ols_fit_predict,
)
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize  # noqa: E402

FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]


def ex1_posterior_1d(x, y, lam, sig2):
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    S = 1.0 / (lam + (1.0 / sig2) * float(np.sum(x * x)))
    m = (1.0 / sig2) * S * float(np.sum(x * y))
    return float(m), float(S)


def ex2_contractie_posterior(lam, sig2):
    rng = np.random.default_rng(0)
    Xa = rng.uniform(-3, 3, size=(10, 1))
    ya = 1.0 + 2.0 * Xa[:, 0] + 0.4 * rng.standard_normal(10)
    Xb = rng.uniform(-3, 3, size=(500, 1))
    yb = 1.0 + 2.0 * Xb[:, 0] + 0.4 * rng.standard_normal(500)
    ta = BayesianLinearRegression(lam=lam, sig2=sig2).fit(Xa, ya).cov_trace()
    tb = BayesianLinearRegression(lam=lam, sig2=sig2).fit(Xb, yb).cov_trace()
    return float(ta), float(tb)


def ex3_acoperire_predictie(level):
    rng = np.random.default_rng(1)
    X_tr = rng.uniform(-3, 3, size=(150, 1))
    y_tr = -1.0 + 2.0 * X_tr[:, 0] + 0.5 * rng.standard_normal(150)
    X_te = rng.uniform(-3, 3, size=(2000, 1))
    y_te = -1.0 + 2.0 * X_te[:, 0] + 0.5 * rng.standard_normal(2000)
    blr = BayesianLinearRegression(lam=1e-3, sig2=0.25).fit(X_tr, y_tr)
    _, lo, hi = blr.predict_interval(X_te, level=level)
    return empirical_coverage(y_te, lo, hi)


def ex4_conformal_acoperire(alpha):
    rng = np.random.default_rng(2)
    X = rng.uniform(-3, 3, size=(400, 1))
    y = 0.5 + 1.5 * X[:, 0] + 0.6 * rng.standard_normal(400)
    X_te = rng.uniform(-3, 3, size=(2000, 1))
    y_te = 0.5 + 1.5 * X_te[:, 0] + 0.6 * rng.standard_normal(2000)
    n = X.shape[0]
    perm = rng.permutation(n)
    cut = n // 2
    tr, cal = perm[:cut], perm[cut:]
    _, lo, hi, _ = conformal_split(X[tr], y[tr], X[cal], y[cal], X_te,
                                   _ols_fit_predict, alpha=alpha)
    return empirical_coverage(y_te, lo, hi)


def ex5_predictie_vs_incredere():
    df = make_latency_dataset(n_per_cond=80, seed=0)
    X = df[FEATURES].to_numpy(dtype=float)
    y = np.log10(df["rtt_ms"].to_numpy(dtype=float))
    Xs, _, _, _ = standardize(X)
    y_hat = _ols_fit_predict(Xs, y, Xs)
    sig2 = float(np.var(y - y_hat))
    blr = BayesianLinearRegression(lam=1e-3, sig2=sig2).fit(Xs, y)
    _, lo_p, hi_p = blr.predict_interval(Xs, level=0.90)
    width_pred = float(np.mean(hi_p - lo_p))
    _, lo_b, hi_b = bootstrap_predict_interval(Xs, y, Xs, _ols_fit_predict,
                                               B=100, level=0.90, seed=1)
    width_conf = float(np.mean(hi_b - lo_b))
    return width_pred, width_conf


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    m, S = ex1_posterior_1d([1.0, 2.0], [2.0, 4.0], lam=0.0, sig2=1.0)
    ck("E1: S = 1/5", abs(S - 0.2) < 1e-12)
    ck("E1: m = 2.0", abs(m - 2.0) < 1e-12)

    tmic, tmare = ex2_contractie_posterior(lam=1e-3, sig2=0.16)
    ck("E2: posteriorul se contracta", tmare < tmic)

    ck("E3: acoperire predictie >= 0.85", ex3_acoperire_predictie(0.90) >= 0.85)
    ck("E4: acoperire conformal >= 0.87", ex4_conformal_acoperire(0.1) >= 0.87)

    wp, wi = ex5_predictie_vs_incredere()
    ck("E5: banda de predictie > banda de incredere", wp > wi)

    print("\nTOATE SOLUTIILE M17 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
