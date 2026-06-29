#!/usr/bin/env python3
"""exercitii.py -- M19 Serii temporale (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul serii_temporale_core.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from serii_temporale_core import (  # noqa: E402
    fit_ar, temporal_split, ar_predict_onestep, persistence_forecast, _ar1_process,
)
from date_sar import make_latency_series  # noqa: E402
from utils import rmse  # noqa: E402


# ---------------------------------------------------------------- Ex.1
def ex1_lag_features(series, p):
    """E1. Construieste de mana matricea de lag-uri (fereastra glisanta), FARA a
    folosi make_lag_features. Pentru x_0..x_{n-1} si ordin p, returneaza (X, y) cu
    X de forma (n-p, p), randul t = [x_{t-1}, x_{t-2}, ..., x_{t-p}], y_t = x_t.
    """
    # TODO: foloseste felii din numpy (lag j -> x[p-1-j : n-1-j])
    raise NotImplementedError("E1: lag features de mana")


# ---------------------------------------------------------------- Ex.2
def ex2_phi_ar1_de_mana(x4):
    """E2. Estimeaza phi pentru AR(1) FARA intercept din 4-5 puncte: phi este
    panta celor mai mici patrate fara intercept a lui x_t pe x_{t-1}, adica
    phi = sum(x_{t-1} x_t) / sum(x_{t-1}^2) peste perechile consecutive.
    `x4` e o lista/array scurt(a). Returneaza un float.
    """
    # TODO: construieste perechile (x_{t-1}, x_t) si aplica formula
    raise NotImplementedError("E2: phi AR(1) de mana")


# ---------------------------------------------------------------- Ex.3
def ex3_split_fara_lookahead(series, train_frac=0.7):
    """E3. Foloseste temporal_split si returneaza (max_idx_train, min_idx_test).
    Trebuie sa respecte max_idx_train < min_idx_test (fara look-ahead).
    """
    # TODO
    raise NotImplementedError("E3: split fara look-ahead")


# ---------------------------------------------------------------- Ex.4
def ex4_ar_bate_persistenta(series, p=2, train_frac=0.75):
    """E4. Imparte TEMPORAL seria, potriveste AR(p) pe train, evalueaza un-pas pe
    test si returneaza (rmse_ar, rmse_persistenta). Foloseste fit_ar,
    ar_predict_onestep, persistence_forecast si rmse din utils.
    """
    # TODO
    raise NotImplementedError("E4: AR vs persistenta")


# ---------------------------------------------------------------- Ex.5
def ex5_rmse_pe_latenta_mea(cond="loss_15", p=3):
    """E5. Pe make_latency_series(cond, length=300, seed=4), split temporal 70/30,
    AR(p) pe train, prognoza un-pas pe test. Returneaza (rmse_ar, rmse_persistenta).
    Asteptare: rmse_ar <= rmse_persistenta (AR foloseste persistenta seriei).
    """
    # TODO
    raise NotImplementedError("E5: RMSE pe latenta mea")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # E1: forme corecte si primul rand
    x = np.arange(8.0)
    X, y = ex1_lag_features(x, 2)
    ck("E1: forma X = (n-p, p) = (6, 2)", X.shape == (6, 2) and y.shape == (6,))
    ck("E1: primul rand = [x1, x0], tinta x2", np.array_equal(X[0], [1.0, 0.0]) and y[0] == 2.0)

    # E2: phi de mana pe un AR(1) curat (phi ~ 0.8)
    xa = _ar1_process(2000, phi=0.8, c=0.0, noise=0.2, seed=5)
    phi_hat = ex2_phi_ar1_de_mana(xa)
    ck("E2: phi AR(1) estimat ~ 0.8 (|d| < 0.05)", abs(phi_hat - 0.8) < 0.05)

    # E3: split fara look-ahead
    mx, mn = ex3_split_fara_lookahead(np.arange(50.0), 0.6)
    ck("E3: max_idx_train < min_idx_test", mx < mn)

    # E4: AR bate persistenta pe un proces AR
    xb = _ar1_process(600, phi=0.8, c=1.0, noise=0.4, seed=6)
    rar, rpe = ex4_ar_bate_persistenta(xb, p=2, train_frac=0.75)
    ck("E4: RMSE_AR < RMSE_persistenta pe proces AR", rar < rpe)

    # E5: pe latenta mea
    r_ar, r_pe = ex5_rmse_pe_latenta_mea("loss_15", 3)
    ck("E5: RMSE_AR <= RMSE_persistenta pe latenta", r_ar <= r_pe + 1e-9)

    print("\nTOATE EXERCITIILE M19 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
