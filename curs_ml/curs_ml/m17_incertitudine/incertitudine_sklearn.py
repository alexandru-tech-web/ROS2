#!/usr/bin/env python3
"""incertitudine_sklearn.py -- validare incrucisata a nucleului M17 cu scikit-learn.

Verifica:
  - media posterioara a BayesianLinearRegression (prior slab) ~ coeficientii lui
    sklearn.linear_model.Ridge cu regularizare mica (potrivire sub toleranta);
  - media posterioara la prior moderat ~ coeficientii lui BayesianRidge din sklearn
    (ambele sunt regresie liniara bayesiana cu prior gaussian; mediile sunt
    apropiate cand precizia zgomotului/prior-ului sunt comparabile).

Daca scikit-learn lipseste, iese 0 (nu e o eroare).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from incertitudine_core import BayesianLinearRegression  # noqa: E402

try:
    from sklearn.linear_model import Ridge, BayesianRidge
except ImportError:
    print("[sklearn] indisponibil -- sar validarea incrucisata (nu e o eroare).")
    sys.exit(0)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    rng = np.random.default_rng(7)
    n, d = 200, 3
    X = rng.uniform(-2, 2, size=(n, d))
    w_true = np.array([1.5, -2.0, 0.7])
    b_true = 0.4
    sig = 0.3
    y = b_true + X @ w_true + sig * rng.standard_normal(n)

    # 1) media posterioara (prior foarte slab) ~ Ridge cu alpha mic
    # In nucleu w = [bias, w1, w2, w3]; Ridge separa interceptul.
    blr = BayesianLinearRegression(lam=1e-6, sig2=sig**2).fit(X, y)
    m = blr.m
    bias_blr, coef_blr = m[0], m[1:]
    ridge = Ridge(alpha=1e-6, fit_intercept=True).fit(X, y)
    ck("coeficientii BLR (prior slab) ~ Ridge(alpha mic)",
       np.allclose(coef_blr, ridge.coef_, atol=1e-3))
    ck("interceptul BLR (prior slab) ~ Ridge(alpha mic)",
       abs(bias_blr - ridge.intercept_) < 1e-3)

    # 2) media posterioara ~ BayesianRidge din sklearn (ambele bayesiene)
    # BayesianRidge estimeaza singur alpha (zgomot) si lambda (prior). Comparam
    # coeficientii (panta) -- mediile posterioare sunt apropiate la N mare.
    br = BayesianRidge().fit(X, y)
    blr2 = BayesianLinearRegression(lam=1e-3, sig2=sig**2).fit(X, y)
    ck("coeficientii BLR ~ sklearn BayesianRidge (panta, atol 0.05)",
       np.allclose(blr2.m[1:], br.coef_, atol=0.05))

    print("\nVALIDARE INCRUCISATA M17 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
