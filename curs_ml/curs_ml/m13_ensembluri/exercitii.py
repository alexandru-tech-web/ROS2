#!/usr/bin/env python3
"""exercitii.py -- M13 Ensembluri (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul ensembluri_core (ciotul,
bagging, boosting) -- NU reimplementa ansamblurile.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from ensembluri_core import (  # noqa: E402
    DecisionStump, BaggingClassifier, GradientBoostingClassifier, _sigmoid, _toy_noisy,
)
from date_sar import make_mission_outcome_dataset  # noqa: E402
from utils import accuracy  # noqa: E402

FEATURES = ["delivered_frac", "p95_ms", "n_drones"]


# ---------------------------------------------------------------- Ex.1
def ex1_bootstrap_indices(n, seed):
    """E1. Un esantion bootstrap: n indici din 0..n-1 trasi CU INLOCUIRE, determinist
    prin numpy.random.default_rng(seed). Returneaza un array de n int.
    """
    # TODO: foloseste rng.integers(0, n, size=n)
    raise NotImplementedError("E1: indici bootstrap")


# ---------------------------------------------------------------- Ex.2
def ex2_oob_fraction(n=2000, seed=0):
    """E2. Fractia de exemple LASATE AFARA (out-of-bag) de un esantion bootstrap de
    marime n: cele care nu apar deloc in indicii din ex1_bootstrap_indices(n, seed).
    Returneaza un float (~0.368 = 1/e pentru n mare).
    """
    # TODO: numara indicii din 0..n-1 care lipsesc din esantion, imparte la n
    raise NotImplementedError("E2: fractia out-of-bag")


# ---------------------------------------------------------------- Ex.3
def ex3_bagging_bate_ciotul(seed=0):
    """E3. Pe _toy_noisy(n=400, seed=11) la antrenare si _toy_noisy(n=400, seed=22)
    la test, antreneaza un singur DecisionStump si un BaggingClassifier(41 cioturi).
    Returneaza (acc_ciot, acc_bagging) pe test. Asteptare: acc_bagging >= acc_ciot.
    """
    # TODO
    raise NotImplementedError("E3: bagging bate ciotul")


# ---------------------------------------------------------------- Ex.4
def ex4_un_pas_boosting(y, p, residual_pred, lr):
    """E4. UN pas de gradient boosting in log-odds, de mana. Date: etichetele y,
    probabilitatile curente p = sigmoid(F), predictia ciotului de regresie pe
    reziduuri residual_pred si rata de invatare lr. Reziduul (gradient negativ al
    pierderii logistice) este r = y - p. Returneaza (residual, F_nou_minus_F), unde
    F_nou - F = lr * residual_pred. Returneaza ambele ca array-uri numpy.
    """
    # TODO: residual = y - p ; delta_F = lr * residual_pred
    raise NotImplementedError("E4: un pas de boosting")


# ---------------------------------------------------------------- Ex.5
def ex5_supra_invatare_boosting():
    """E5. Pe make_mission_outcome_dataset(n=600, seed=3), split 75/25 (seed 0),
    antreneaza GradientBoostingClassifier(n_estimators=300, learning_rate=0.5).
    Cu staged_decision_function pe X_TEST, intoarce (test_err_la_120, test_err_la_300).
    Lectie: dupa un punct, pasii in plus NU mai imbunatatesc testul desi eroarea de
    train continua sa scada -- capcana supra-invatarii la boosting. Asteptare:
    test_err_la_300 >= test_err_la_120 - 0.01 (coada nu mai aduce castig, uneori pierde).
    """
    # TODO: foloseste staged_decision_function pe X_test, _sigmoid + prag 0.5, pasii 120 si 300
    raise NotImplementedError("E5: supra-invatare la boosting")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    idx = ex1_bootstrap_indices(50, seed=0)
    ck("E1: 50 indici in 0..49, cu inlocuire (au repetitii)",
       len(idx) == 50 and idx.min() >= 0 and idx.max() <= 49 and len(set(idx.tolist())) < 50)
    idx2 = ex1_bootstrap_indices(50, seed=0)
    ck("E1: determinist la aceeasi samanta", np.array_equal(idx, idx2))

    oob = ex2_oob_fraction(n=3000, seed=1)
    ck("E2: fractia out-of-bag ~ 1/e (0.368 +/- 0.03)", abs(oob - 1.0 / np.e) < 0.03)

    acc_ciot, acc_bag = ex3_bagging_bate_ciotul()
    ck("E3: bagging >= ciot pe date zgomotoase", acc_bag >= acc_ciot - 1e-9)

    y = np.array([1.0, 0.0, 1.0, 0.0])
    p = np.array([0.6, 0.3, 0.4, 0.5])
    rp = np.array([0.4, -0.3, 0.6, -0.5])
    residual, dF = ex4_un_pas_boosting(y, p, rp, lr=0.5)
    ck("E4: reziduul = y - p", np.allclose(residual, y - p))
    ck("E4: delta_F = lr * residual_pred", np.allclose(dF, 0.5 * rp))

    e120, e300 = ex5_supra_invatare_boosting()
    ck("E5: pasii in plus NU mai imbunatatesc testul (plateau)", e300 >= e120 - 0.01)

    print("\nTOATE EXERCITIILE M13 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
