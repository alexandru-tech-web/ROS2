#!/usr/bin/env python3
"""regresie_liniara_sklearn.py -- VALIDARE incrucisata a nucleului M05.

Rulam ACEEASI sarcina (regresie liniara) si cu nucleul nostru
(regresie_liniara_core) si cu sklearn.linear_model.LinearRegression, pe aceleasi
date, si ASERTAM ca rezultatele coincid sub o toleranta:
  - coeficientii (bias + pante) aproape egali;
  - predictiile aproape egale (RMSE intre ele foarte mic);
  - R^2 raportat aproape identic.

In plus aratam ca varianta noastra de gradient descent ajunge la aceeasi solutie.

scikit-learn e permis DOAR aici (fisier de validare), niciodata in core.
Ruleaza: python3 regresie_liniara_sklearn.py   (0 = coincid, non-0 = divergenta).
"""
import os
import sys

import numpy as np
from sklearn.linear_model import LinearRegression

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import add_bias, r2_score, rmse, standardize  # noqa: E402
from regresie_liniara_core import (  # noqa: E402
    RegresieLiniara,
    fit_gradient_descent,
    fit_normal_equations,
    predict,
)


def main():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # date sintetice cu w cunoscut
    g = np.random.default_rng(7)
    n, d = 350, 4
    X = g.normal(0.0, 1.0, size=(n, d))
    w_true = g.normal(0.0, 2.0, size=d)
    y = 2.0 + X @ w_true + g.normal(0.0, 0.5, size=n)

    # ---- nucleu: ecuatii normale pe matricea cu bias
    Xb = add_bias(X)
    w_core = fit_normal_equations(Xb, y)
    yhat_core = predict(Xb, w_core)

    # ---- sklearn (gestioneaza interceptul intern)
    sk = LinearRegression().fit(X, y)
    w_sklearn = np.concatenate([[sk.intercept_], sk.coef_])
    yhat_sk = sk.predict(X)

    print("coef nucleu  (bias, pante):", np.round(w_core, 5))
    print("coef sklearn (bias, pante):", np.round(w_sklearn, 5))

    ck("coeficienti nucleu ~ sklearn (atol 1e-6)",
       np.allclose(w_core, w_sklearn, atol=1e-6))
    ck("predictii nucleu ~ sklearn (RMSE < 1e-8)",
       rmse(yhat_core, yhat_sk) < 1e-8)
    r2_core = r2_score(y, yhat_core)
    r2_sk = sk.score(X, y)
    print("R^2 nucleu = %.6f | R^2 sklearn = %.6f" % (r2_core, r2_sk))
    ck("R^2 nucleu ~ R^2 sklearn (|.| < 1e-9)", abs(r2_core - r2_sk) < 1e-9)

    # ---- gradient descent (pe date standardizate) ~ sklearn pe date standardizate
    Xs, _, _, _ = standardize(X)
    Xbs = add_bias(Xs)
    w_gd = fit_gradient_descent(Xbs, y, alpha=0.2, n_iter=30000, tol=1e-13)
    sk_std = LinearRegression().fit(Xs, y)
    w_sk_std = np.concatenate([[sk_std.intercept_], sk_std.coef_])
    ck("gradient descent (standardizat) ~ sklearn (atol 1e-4)",
       np.allclose(w_gd, w_sk_std, atol=1e-4))

    # ---- API de clasa al nucleului ~ sklearn pe predictii
    model = RegresieLiniara(method="normal").fit(X, y)
    ck("RegresieLiniara.predict ~ sklearn.predict (RMSE < 1e-8)",
       rmse(model.predict(X), yhat_sk) < 1e-8)

    print("\nVALIDARE INCRUCISATA OK: %d verificari (nucleu == sklearn)." % ok)
    return ok


if __name__ == "__main__":
    try:
        main()
        print("PASS")
        sys.exit(0)
    except AssertionError as e:
        print(e)
        print("FAIL")
        sys.exit(1)
