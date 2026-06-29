#!/usr/bin/env python3
"""optimizare_sklearn.py -- validare incrucisata a nucleului M02 cu scikit-learn.

Nucleul (optimizare_core.py) implementeaza optimizatorii de la zero. Aici rulam
ACEEASI sarcina cu scikit-learn si ASERTAM ca rezultatele coincid sub o toleranta.

Doua verificari independente, pe aceleasi date:
1. Minimizarea unei patratice f(w)=0.5 w^T A w - b^T w. Adam din nucleu trebuie
   sa gaseasca acelasi minim ca solutia in forma inchisa w* = A^{-1} b pe care o
   da numpy/scipy (scikit-learn nu rezolva direct o patratica abstracta, deci
   referinta aici e algebra liniara). Confirmam si ca diferentele finite din
   nucleu se potrivesc cu gradientul analitic.
2. O regresie liniara minimizata cu GD din nucleu, comparata cu:
   - sklearn.linear_model.LinearRegression (forma inchisa, referinta de aur);
   - sklearn.linear_model.SGDRegressor (acelasi spirit: coborare pe gradient).
   Coeficientii trebuie sa coincida sub toleranta.

scikit-learn este permis DOAR aici (in nucleu este interzis).

Ruleaza:
  /home/ubuntu/ros2_ws/.venv_ml/bin/python optimizare_sklearn.py   (iesire 0 = PASS)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from optimizare_core import (adam, check_grad, gradient_descent, quadratic_grad,
                             quadratic_solution, quadratic_value)
from utils import rng

from sklearn.linear_model import LinearRegression, SGDRegressor


def _make_regression(n=300, d=4, noise=0.01, seed=7):
    g = rng(seed)
    X = g.normal(size=(n, d))
    w_true = g.normal(size=d)
    y = X @ w_true + noise * g.normal(size=n)
    return X, y, w_true


def main():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    print("=== Validare 1: patratica f(w)=0.5 w^T A w - b^T w ===")
    A = np.array([[4.0, 1.0, 0.0],
                  [1.0, 3.0, 1.0],
                  [0.0, 1.0, 2.0]])
    b = np.array([1.0, 0.0, -1.0])
    w_star = quadratic_solution(A, b)            # referinta: algebra liniara

    f = lambda w: quadratic_value(w, A, b)
    grad = lambda w: quadratic_grad(w, A, b)

    err_fd = check_grad(f, grad, np.array([0.3, -0.7, 1.1]), h=1e-5)
    print("  gradient analitic vs diferente finite: eroare = %.2e" % err_fd)
    ck("gradientul analitic se potriveste cu diferentele finite (< 1e-5)", err_fd < 1e-5)

    w_adam, _ = adam(grad, np.zeros(3), alpha=0.05, n_iter=6000)
    print("  w* (algebra)  = %s" % np.array2string(w_star, precision=5))
    print("  w (Adam core) = %s" % np.array2string(w_adam, precision=5))
    ck("Adam (core) == w* analitic (atol 1e-3)", np.allclose(w_adam, w_star, atol=1e-3))

    print("\n=== Validare 2: regresie liniara, GD (core) vs scikit-learn ===")
    X, y, w_true = _make_regression(n=300, d=4, noise=0.01, seed=7)

    # referinta de aur: solutie in forma inchisa (sklearn fara intercept)
    lr = LinearRegression(fit_intercept=False).fit(X, y)
    w_closed = lr.coef_

    # GD din nucleu pe pierderea patratica medie L(w) = (1/n) ||Xw - y||^2
    n = X.shape[0]
    grad_reg = lambda w: (2.0 / n) * X.T @ (X @ w - y)
    val_reg = lambda w: float(np.mean((X @ w - y) ** 2))
    w_gd, hist = gradient_descent(grad_reg, np.zeros(X.shape[1]), eta=0.1,
                                  n_iter=2000, value=val_reg)

    # SGD din scikit-learn (acelasi spirit, alt drum)
    sk = SGDRegressor(loss="squared_error", penalty=None, fit_intercept=False,
                      learning_rate="invscaling", eta0=0.01, max_iter=2000,
                      tol=1e-7, random_state=0).fit(X, y)
    w_sk = sk.coef_

    print("  w (forma inchisa, sklearn LR) = %s" % np.array2string(w_closed, precision=4))
    print("  w (GD core)                   = %s" % np.array2string(w_gd, precision=4))
    print("  w (SGDRegressor sklearn)      = %s" % np.array2string(w_sk, precision=4))
    print("  pierdere GD core: start=%.4f -> final=%.6f" % (hist[0], hist[-1]))

    ck("GD core == forma inchisa LinearRegression (atol 1e-3)",
       np.allclose(w_gd, w_closed, atol=1e-3))
    ck("GD core ~ SGDRegressor sklearn (atol 5e-2)",
       np.allclose(w_gd, w_sk, atol=5e-2))
    ck("GD core ~ adevarul generator (atol 1e-2)",
       np.allclose(w_gd, w_true, atol=1e-2))

    print("\nVALIDARE INCRUCISATA M02 OK: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
