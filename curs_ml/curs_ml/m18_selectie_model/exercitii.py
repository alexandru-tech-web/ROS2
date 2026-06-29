#!/usr/bin/env python3
"""exercitii.py -- M18 Selectie de model si reglare hiperparametri (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul selectie_model_core.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # .../m18_selectie_model

from selectie_model_core import (  # noqa: E402
    grid_search_cv, nested_cv, _poly_design, gaussian_neg2ll,
)
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize  # noqa: E402


def _fit_predict_poly_1d(X_tr, y_tr, X_te, deg):
    """Adaptor fit_predict: polinom de grad `deg` pe prima coloana a lui X."""
    x_tr = np.asarray(X_tr, dtype=float)[:, 0]
    x_te = np.asarray(X_te, dtype=float)[:, 0]
    Phi = _poly_design(x_tr, deg)
    w, *_ = np.linalg.lstsq(Phi, y_tr, rcond=None)
    return _poly_design(x_te, deg) @ w


# ---------------------------------------------------------------- Ex.1
def ex1_alege_grad(x, y, grid, k=5, seed=0):
    """E1. Foloseste grid_search_cv cu _fit_predict_poly_1d ca sa alegi gradul
    polinomului cu RMSE de validare incrucisata minim. `x` e 1D; reshape la (-1, 1).
    Returneaza gradul ales (int).
    """
    # TODO: x.reshape(-1,1); apeleaza grid_search_cv; intoarce primul element (best_hp)
    raise NotImplementedError("E1: grid search peste gradul polinomului")


# ---------------------------------------------------------------- Ex.2
def ex2_aic(neg2ll, k):
    """E2. AIC = 2k - 2 ln L. Primesti DIRECT -2 ln L (neg2ll). Returneaza float.
    """
    # TODO
    raise NotImplementedError("E2: AIC din log-verosimilitate")


# ---------------------------------------------------------------- Ex.3
def ex3_alege_model(rss_a, k_a, rss_b, k_b, n, criteriu="aic"):
    """E3. Calculeaza AIC sau BIC (criteriu in {'aic','bic'}) pentru doua modele
    gaussiene din RSS (foloseste gaussian_neg2ll pentru -2 ln L) si returneaza
    'A' sau 'B' (cel cu valoarea criteriului mai MICA).
    Reaminteste: AIC = 2k + (-2lnL); BIC = k*ln(n) + (-2lnL).
    """
    # TODO
    raise NotImplementedError("E3: alegerea modelului dupa AIC/BIC")


# ---------------------------------------------------------------- Ex.4
def ex4_penalizare_pe_parametru(n):
    """E4. Penalizarea ADAUGATA per parametru in plus: (pen_aic, pen_bic).
    AIC adauga 2 per parametru; BIC adauga ln(n). Returneaza (float, float).
    """
    # TODO
    raise NotImplementedError("E4: penalizarea per parametru")


# ---------------------------------------------------------------- Ex.5
def ex5_eroare_onesta():
    """E5. Pe make_latency_dataset(n_per_cond=120, seed=0): prezice log10(rtt_ms) din
    distance_m STANDARDIZATA. Alege gradul cu grid=[1,2,3,4,5,6].
    Returneaza (err_selectie, err_onesta):
      - err_selectie = scorul minim din grid_search_cv (k=5, seed=0) -- OPTIMIST;
      - err_onesta   = media nested_cv (k_outer=5, k_inner=4, seed=0) -- ONEST.
    Asteptare: err_onesta >= err_selectie.
    """
    # TODO: construieste X (distance_m), y = log10(rtt_ms), standardize, apoi
    #       grid_search_cv si nested_cv cu _fit_predict_poly_1d.
    raise NotImplementedError("E5: eroarea onesta cu nested CV")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    g = np.random.default_rng(0)
    x = g.uniform(-2, 2, 80)
    y = 0.5 * x ** 3 - x + 1.0 + 0.3 * g.standard_normal(80)
    ck("E1: grid search alege gradul 3 pe cubica zgomotoasa",
       ex1_alege_grad(x, y, [1, 2, 3, 4, 5], k=5, seed=0) == 3)

    ck("E2: AIC(-2lnL=218, k=3) = 224", abs(ex2_aic(218.0, 3) - 224.0) < 1e-9)

    ck("E3 (AIC): modelul simplu A castiga la potrivire egala",
       ex3_alege_model(52.0, 3, 50.0, 6, 100, "aic") == "A")
    ck("E3 (BIC): modelul simplu A castiga la potrivire egala",
       ex3_alege_model(52.0, 3, 50.0, 6, 100, "bic") == "A")

    pa, pb = ex4_penalizare_pe_parametru(100)
    ck("E4: penalizarea AIC per parametru = 2", abs(pa - 2.0) < 1e-12)
    ck("E4: BIC penalizeaza mai tare ca AIC la n=100", pb > pa)

    sel, onest = ex5_eroare_onesta()
    ck("E5: eroarea onesta (nested) >= eroarea de selectie", onest >= sel - 1e-9)

    print("\nTOATE EXERCITIILE M18 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
