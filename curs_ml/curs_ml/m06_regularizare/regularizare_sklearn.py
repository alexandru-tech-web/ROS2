#!/usr/bin/env python3
"""regularizare_sklearn.py -- validare incrucisata a nucleului M06 cu scikit-learn.

Ruleaza nucleul (ridge_fit, lasso_fit) si echivalentele sklearn pe aceleasi date
si verifica:
  - Ridge: coeficientii nostri ~ sklearn.linear_model.Ridge (acelasi obiectiv
    ||Xw-y||^2 + alpha||w||^2, fit_intercept=False) sub toleranta;
  - Lasso: ACELASI suport (tipar de zerouri) ca sklearn.linear_model.Lasso, cu
    maparea alpha = lam / n (sklearn foloseste 1/(2n) inaintea pierderii patratice,
    nucleul nostru 1/2). Comparam suportul, nu valorile exacte (numeric sensibil).

Iesire 0 daca toate potrivirile trec.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from regularizare_core import ridge_fit, lasso_fit  # noqa: E402

try:
    from sklearn.linear_model import Ridge, Lasso
except ImportError:
    print("[sklearn] indisponibil in acest mediu -- sar validarea incrucisata (nu e o eroare).")
    sys.exit(0)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    rng = np.random.default_rng(1)
    n, p = 80, 6
    X = rng.standard_normal((n, p))
    X = (X - X.mean(axis=0)) / X.std(axis=0)
    w_true = np.array([4.0, 0.0, -3.0, 0.0, 1.5, 0.0])
    y = X @ w_true + 0.1 * rng.standard_normal(n)
    y = y - y.mean()

    # Ridge: potrivire directa de coeficienti
    for alpha in [1.0, 10.0, 100.0]:
        w_core = ridge_fit(X, y, alpha)
        w_sk = Ridge(alpha=alpha, fit_intercept=False).fit(X, y).coef_
        ck("ridge core ~ sklearn (alpha=%g)" % alpha, np.allclose(w_core, w_sk, atol=1e-6))

    # Lasso: acelasi suport (tipar de zerouri), maparea alpha = lam / n
    for lam in [5.0, 15.0, 30.0]:
        w_core = lasso_fit(X, y, lam=lam, n_iter=2000)
        w_sk = Lasso(alpha=lam / n, fit_intercept=False, max_iter=20000).fit(X, y).coef_
        supp_core = np.abs(w_core) > 1e-6
        supp_sk = np.abs(w_sk) > 1e-6
        ck("lasso core: acelasi suport ca sklearn (lam=%g)" % lam,
           np.array_equal(supp_core, supp_sk))

    print("\nVALIDARE INCRUCISATA M06 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
