#!/usr/bin/env python3
"""exercitii.py -- M07 Evaluare si validare (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul evaluare_validare_core.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from evaluare_validare_core import (  # noqa: E402
    kfold_indices, cross_val_score, learning_curve, _ols_fit_predict,
)
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize  # noqa: E402


# ---------------------------------------------------------------- Ex.1
def ex1_kfold_manual(n, k):
    """E1. k-fold FARA amestecare, de mana: imparte 0..n-1 in k blocuri contigue
    (primele n%k blocuri au un element in plus). Returneaza o lista de array-uri cu
    indicii de TEST ai fiecarui fald. NU folosi kfold_indices.
    """
    # TODO: foloseste numpy.array_split pe numpy.arange(n)
    raise NotImplementedError("E1: k-fold manual contiguu")


# ---------------------------------------------------------------- Ex.2
def ex2_rmse_mae(y_true, y_pred):
    """E2. Implementeaza RMSE si MAE de la zero (fara utils). Returneaza (rmse, mae).
    """
    # TODO
    raise NotImplementedError("E2: rmse si mae de la zero")


# ---------------------------------------------------------------- Ex.3
def ex3_k_pentru_loocv(n):
    """E3. Ce valoare a lui k face k-fold sa fie identic cu LOOCV? Returneaza int.
    """
    # TODO
    raise NotImplementedError("E3: k pentru LOOCV")


# ---------------------------------------------------------------- Ex.4
def ex4_cv_mean_rmse(X, y, k=5, seed=0):
    """E4. Media RMSE de validare incrucisata a modelului liniar auxiliar
    (_ols_fit_predict) pe (X, y), cu k falduri. Foloseste cross_val_score.
    Returneaza un float.
    """
    # TODO
    raise NotImplementedError("E4: media RMSE CV")


# ---------------------------------------------------------------- Ex.5
def ex5_gol_invatare():
    """E5. Pe make_latency_dataset(n_per_cond=150, seed=0), feature-uri standardizate
    -> log10(rtt_ms), calculeaza eroarea de VALIDARE la set mic (10) si la set mare
    (600) cu learning_curve. Returneaza (val_mic, val_mare).
    Asteptare: val_mare <= val_mic (mai multe date ajuta).
    """
    # TODO
    raise NotImplementedError("E5: golul curbei de invatare")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    folds = ex1_kfold_manual(10, 3)
    allt = np.concatenate(folds)
    ck("E1: 3 falduri acopera 0..9 o data",
       len(folds) == 3 and sorted(allt.tolist()) == list(range(10)))

    r, m = ex2_rmse_mae([1.0, 2.0, 3.0], [1.0, 4.0, 3.0])
    # erori: 0, 2, 0 -> rmse = sqrt(4/3) ~ 1.1547 ; mae = 2/3
    ck("E2: rmse = sqrt(4/3)", abs(r - np.sqrt(4.0 / 3.0)) < 1e-12)
    ck("E2: mae = 2/3", abs(m - 2.0 / 3.0) < 1e-12)

    ck("E3: k pentru LOOCV pe n=7 este 7", ex3_k_pentru_loocv(7) == 7)

    rng = np.random.default_rng(0)
    X = rng.uniform(-2, 2, (120, 3))
    y = X @ np.array([1.0, -1.0, 0.5]) + 0.05 * rng.standard_normal(120)
    ck("E4: media RMSE CV mica pe date liniare", ex4_cv_mean_rmse(X, y, 5, 0) < 0.2)

    vm, vM = ex5_gol_invatare()
    ck("E5: validarea la set mare <= la set mic", vM <= vm + 1e-9)

    print("\nTOATE EXERCITIILE M07 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
