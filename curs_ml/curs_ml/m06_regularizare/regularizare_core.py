#!/usr/bin/env python3
"""regularizare_core.py -- nucleul M06, numpy pur (scikit-learn INTERZIS).

Regularizare pentru regresie liniara: Ridge (penalizare L2, forma inchisa) si
Lasso (penalizare L1, sparsitate, prin coordinate descent cu soft-thresholding).

Model: minimizeaza ||X w - y||^2 + lam * pen(w), unde
  - Ridge: pen(w) = ||w||_2^2 -> solutie inchisa (X^T X + lam I) w = X^T y;
  - Lasso: pen(w) = ||w||_1 -> fara forma inchisa; coordinate descent.

CONVENTIE: aceste nuclee presupun X deja STANDARDIZAT (coloane medie 0, abatere 1)
si y centrat (medie 0), deci NU exista coloana de bias si penalizarea e corecta pe
toti coeficientii (vezi teorie.md sectiunea 2). Pentru date brute, standardizeaza
intai cu utils.standardize.

Determinism: niciun aleator in potriviri. _selftest() verifica:
  - Ridge la lam=0 == OLS (cele mai mici patrate);
  - ||w_ridge|| scade monoton cand lam creste (micsorare);
  - soft_threshold pe valori cunoscute;
  - Lasso aduce coeficienti la EXACT 0 (sparsitate) cand lam e mare;
  - pe un model rar (coeficienti adevarati cu zerouri) Lasso recupereaza suportul.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python regularizare_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml


# ============================================================ OLS si RIDGE
def ols_fit(X, y):
    """Cele mai mici patrate w = argmin ||Xw - y||^2 (via lstsq, robust)."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    w, *_ = np.linalg.lstsq(X, y, rcond=None)
    return w


def ridge_fit(X, y, lam):
    """Ridge: w = (X^T X + lam I)^-1 X^T y (forma inchisa). lam >= 0."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    p = X.shape[1]
    A = X.T @ X + lam * np.eye(p)
    b = X.T @ y
    return np.linalg.solve(A, b)


# ============================================================ LASSO (coordinate descent)
def soft_threshold(z, gamma):
    """Operatorul de prag moale: sign(z) * max(|z| - gamma, 0). gamma >= 0."""
    return np.sign(z) * np.maximum(np.abs(z) - gamma, 0.0)


def lasso_fit(X, y, lam, n_iter=500, tol=1e-8):
    """Lasso prin coordinate descent cu soft-thresholding.

    Minimizeaza (1/(2)) ||Xw - y||^2 + lam ||w||_1 (conventia cu 1/2; lam-ul scaleaza
    diferit de Ridge). Presupune X standardizat. Itereaza pe coordonate:
        w_j <- soft_threshold(rho_j, lam) / (x_j^T x_j)
    unde rho_j = x_j^T (y - X w + w_j x_j) este corelatia reziduului partial.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    n, p = X.shape
    w = np.zeros(p)
    col_norm2 = np.sum(X ** 2, axis=0)         # x_j^T x_j
    for _ in range(n_iter):
        w_old = w.copy()
        for j in range(p):
            r_j = y - X @ w + w[j] * X[:, j]    # reziduu fara contributia lui j
            rho_j = X[:, j] @ r_j
            if col_norm2[j] > 0:
                w[j] = soft_threshold(rho_j, lam) / col_norm2[j]
        if np.max(np.abs(w - w_old)) < tol:
            break
    return w


# ============================================================ SELFTEST
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    rng = np.random.default_rng(0)
    n, p = 60, 5
    X = rng.standard_normal((n, p))
    X = (X - X.mean(axis=0)) / X.std(axis=0)        # standardizat
    w_true = np.array([3.0, 0.0, -2.0, 0.0, 0.0])   # model RAR (3 zerouri)
    y = X @ w_true + 0.1 * rng.standard_normal(n)
    y = y - y.mean()

    # Ridge la lam=0 == OLS
    ck("ridge(lam=0) == OLS", np.allclose(ridge_fit(X, y, 0.0), ols_fit(X, y), atol=1e-8))

    # micsorare: ||w_ridge|| scade cand lam creste
    norms = [np.linalg.norm(ridge_fit(X, y, lam)) for lam in [0.0, 1.0, 10.0, 100.0, 1000.0]]
    ck("ridge: ||w|| scade monoton cu lam", all(norms[i] > norms[i + 1] for i in range(len(norms) - 1)))

    # soft_threshold pe valori cunoscute
    ck("soft_threshold(5, 2) = 3", abs(soft_threshold(5.0, 2.0) - 3.0) < 1e-12)
    ck("soft_threshold(-5, 2) = -3", abs(soft_threshold(-5.0, 2.0) + 3.0) < 1e-12)
    ck("soft_threshold(1, 2) = 0 (in zona moarta)", abs(soft_threshold(1.0, 2.0)) < 1e-12)

    # Lasso: lam mic recupereaza aproape OLS pe coeficientii nenuli
    w_small = lasso_fit(X, y, lam=0.5)
    ck("lasso(lam mic): coeficientii mari ~ semnul corect",
       w_small[0] > 1.0 and w_small[2] < -1.0)

    # Lasso: lam mare -> sparsitate (unii coeficienti EXACT 0)
    w_big = lasso_fit(X, y, lam=20.0)
    n_zero = int(np.sum(np.abs(w_big) < 1e-8))
    ck("lasso(lam mare): produce zerouri exacte (sparsitate)", n_zero >= 2)

    # pe model rar, Lasso pune la 0 macar 2 dintre cei 3 coeficienti adevarati nuli
    w_mid = lasso_fit(X, y, lam=5.0)
    zeros_true = [1, 3, 4]
    n_zeroed_true = int(np.sum([abs(w_mid[j]) < 1e-6 for j in zeros_true]))
    ck("lasso: zerorizeaza coeficienti adevarati nuli (>=2 din 3)", n_zeroed_true >= 2)

    # Ridge NU produce zerouri exacte (doar micsoreaza) -- contrast cu Lasso
    w_ridge = ridge_fit(X, y, 5.0)
    ck("ridge: NU produce zerouri exacte (contrast cu Lasso)",
       int(np.sum(np.abs(w_ridge) < 1e-8)) == 0)

    print("\nTOATE VERIFICARILE regularizare_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
