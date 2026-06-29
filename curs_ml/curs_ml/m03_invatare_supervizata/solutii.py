#!/usr/bin/env python3
"""solutii.py -- M03 Cadrul invatarii supervizate (SOLUTIILE complete).

Rezolvarea exercitiilor din exercitii.py. Rulat cu venv-ul ML trebuie sa treaca
(exit 0). Uita-te aici DUPA ce ai incercat singur.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python solutii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from invatare_supervizata_core import (  # noqa: E402
    squared_loss, hinge_loss, logistic_loss, fit_poly, predict_poly,
    bias_variance_decomposition,
)


# ---------------------------------------------------------------- E1
def ex1_risc_empiric_patratic(y_true, y_pred):
    return float(np.mean(squared_loss(y_true, y_pred)))


# ---------------------------------------------------------------- E2
def ex2_eroare_clasificator_prag(scores, y_true, threshold=0.0):
    scores = np.asarray(scores, dtype=float)
    y_true = np.asarray(y_true)
    pred = (scores > threshold).astype(int)
    return float(np.mean(pred != y_true))


# ---------------------------------------------------------------- E3
def ex3_compara_surogate(score):
    h = float(hinge_loss([1.0], [float(score)])[0])     # y = +1
    lg = float(logistic_loss([1.0], [float(score)])[0])  # y = 1
    return h, lg


# ---------------------------------------------------------------- E4
def ex4_grad_optim_biasvar(f_true, x_grid, sigma, n_train, degrees,
                           n_datasets=400, seed=0):
    totals = []
    for d in degrees:
        res = bias_variance_decomposition(f_true, x_grid, degree=d, sigma=sigma,
                                          n_train=n_train, n_datasets=n_datasets, seed=seed)
        totals.append(res["total"])
    return int(degrees[int(np.argmin(totals))])


# ---------------------------------------------------------------- E5
def ex5_efect_n_train_variance(f_true, x_grid, sigma, degree, n_trains,
                               n_datasets=400, seed=0):
    out = []
    for n in n_trains:
        res = bias_variance_decomposition(f_true, x_grid, degree=degree, sigma=sigma,
                                          n_train=n, n_datasets=n_datasets, seed=seed)
        out.append(res["variance"])
    return out


# ---------------------------------------------------------------- E6
def ex6_polinom_underfit_overfit(f_true, sigma, n_train, seed=0):
    g = np.random.default_rng(seed)
    x_tr = g.uniform(-1.0, 1.0, size=n_train)
    y_tr = f_true(x_tr) + g.normal(0.0, sigma, size=n_train)
    x_grid = np.linspace(-0.9, 0.9, 200)
    f_grid = f_true(x_grid)
    w1 = fit_poly(x_tr, y_tr, degree=1, ridge=1e-8)
    w12 = fit_poly(x_tr, y_tr, degree=12, ridge=1e-8)
    rmse1 = float(np.sqrt(np.mean((predict_poly(w1, x_grid) - f_grid) ** 2)))
    rmse12 = float(np.sqrt(np.mean((predict_poly(w12, x_grid) - f_grid) ** 2)))
    return rmse1, rmse12


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    r = ex1_risc_empiric_patratic([3.0, 0.0, -2.0], [1.0, 0.0, 1.0])
    ck("E1: R_emp patratic = 13/3", abs(r - 13.0 / 3.0) < 1e-12)

    e = ex2_eroare_clasificator_prag([0.4, -0.2, 1.1, -0.9], [1, 0, 1, 1], threshold=0.0)
    ck("E2: eroare 0-1 cu prag = 0.25", abs(e - 0.25) < 1e-12)

    h, lg = ex3_compara_surogate(0.0)
    ck("E3: hinge(0)=1, logistica(0)=log2",
       abs(h - 1.0) < 1e-12 and abs(lg - np.log(2)) < 1e-12)

    def f_true(x):
        return np.sin(1.5 * np.pi * np.asarray(x, dtype=float))

    x_grid = np.linspace(-0.9, 0.9, 25)
    sigma = 0.2

    best = ex4_grad_optim_biasvar(f_true, x_grid, sigma, n_train=20,
                                  degrees=list(range(0, 10)), n_datasets=400, seed=5)
    ck("E4: gradul optim e interior (1 <= d* <= 8)", 1 <= best <= 8)

    variances = ex5_efect_n_train_variance(f_true, x_grid, sigma, degree=6,
                                           n_trains=[15, 40, 120], n_datasets=300, seed=5)
    ck("E5: varianta scade cu n_train", variances[0] > variances[1] > variances[2])

    rmse1, rmse12 = ex6_polinom_underfit_overfit(f_true, sigma, n_train=12, seed=5)
    ck("E6: grad 1 si grad 12 dau rmse pozitiv", rmse1 > 0 and rmse12 > 0)

    print("\nTOATE SOLUTIILE M03 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
