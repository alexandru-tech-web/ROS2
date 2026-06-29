#!/usr/bin/env python3
"""exercitii.py -- M06 Regularizare (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul regularizare_core unde se cere.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from regularizare_core import ridge_fit, ols_fit, lasso_fit  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize  # noqa: E402


# ---------------------------------------------------------------- Ex.1
def ex1_ridge_de_mana(X, y, lam):
    """E1. Implementeaza Ridge in forma inchisa, FARA a apela ridge_fit:
    w = (X^T X + lam I)^-1 X^T y. Foloseste numpy.linalg.solve. Returneaza w.
    """
    # TODO
    raise NotImplementedError("E1: ridge in forma inchisa")


# ---------------------------------------------------------------- Ex.2
def ex2_soft_threshold(z, gamma):
    """E2. Operatorul de prag moale: sign(z) * max(|z| - gamma, 0). Vectorizat.
    """
    # TODO
    raise NotImplementedError("E2: soft threshold")


# ---------------------------------------------------------------- Ex.3
def ex3_norme_ridge(X, y, lams):
    """E3. Pentru o lista de lambda, returneaza lista normelor L2 ale coeficientilor
    Ridge (foloseste ridge_fit). Scop: micsorarea (norma scade cu lam).
    """
    # TODO
    raise NotImplementedError("E3: norme ridge vs lam")


# ---------------------------------------------------------------- Ex.4
def ex4_nenule_lasso(X, y, lams):
    """E4. Pentru o lista de lambda, returneaza lista numarului de coeficienti Lasso
    nenuli (|w_j| > 1e-6) la fiecare lambda (foloseste lasso_fit). Scop: sparsitate
    crescatoare (mai putine nenule la lam mai mare).
    """
    # TODO
    raise NotImplementedError("E4: numar de coeficienti nenuli Lasso")


# ---------------------------------------------------------------- Ex.5
def ex5_ridge_vs_ols_pe_date():
    """E5. Pe make_latency_dataset(n_per_cond=120, seed=0), feature-uri
    standardizate ['loss_pct','base_lat_ms','jitter_ms','distance_m'] -> tinta
    log10(rtt_ms) centrata. Returneaza (norma_ols, norma_ridge_lam10).
    Asteptare: norma_ridge < norma_ols.
    """
    # TODO
    raise NotImplementedError("E5: ridge vs ols pe datele mele")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    rng = np.random.default_rng(0)
    X = rng.standard_normal((50, 4))
    X = (X - X.mean(0)) / X.std(0)
    y = X @ np.array([2.0, 0.0, -1.0, 0.0]) + 0.1 * rng.standard_normal(50)
    y = y - y.mean()

    ck("E1: ridge de mana == ridge_fit", np.allclose(ex1_ridge_de_mana(X, y, 3.0), ridge_fit(X, y, 3.0), atol=1e-9))
    ck("E2: soft_threshold(5,2)=3, (-1,2)=0",
       abs(float(ex2_soft_threshold(np.array([5.0]), 2.0)[0]) - 3.0) < 1e-12
       and abs(float(ex2_soft_threshold(np.array([-1.0]), 2.0)[0])) < 1e-12)

    lams = [0.1, 1.0, 10.0, 100.0]
    norme = ex3_norme_ridge(X, y, lams)
    ck("E3: norma Ridge scade cu lam", all(norme[i] > norme[i + 1] for i in range(len(norme) - 1)))

    nz = ex4_nenule_lasso(X, y, [0.5, 5.0, 30.0])
    ck("E4: nenule Lasso scad cu lam", nz[0] >= nz[1] >= nz[2] and nz[-1] < nz[0])

    n_ols, n_ridge = ex5_ridge_vs_ols_pe_date()
    ck("E5: norma Ridge < norma OLS pe datele mele", n_ridge < n_ols)

    print("\nTOATE EXERCITIILE M06 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
