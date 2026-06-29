#!/usr/bin/env python3
"""exercitii.py -- M08 Regresie logistica (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul regresie_logistica_core.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from regresie_logistica_core import (  # noqa: E402
    sigmoid, cross_entropy_loss, LogisticRegressionGD,
)
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import standardize, add_bias, precision_recall_f1  # noqa: E402

FEATURES = ["p95_ms", "loss_frac", "jitter_ms", "distance_m", "mw_zenoh"]


# ---------------------------------------------------------------- Ex.1
def ex1_sigmoid_proprietati(z):
    """E1. Foloseste sigmoid din nucleu. Returneaza (sigmoid(z), 1 - sigmoid(-z)).
    Cele doua trebuie sa fie egale (simetria sigmoidei). Verifica si ca sigmoid(0)=0.5.
    """
    # TODO: apeleaza sigmoid din regresie_logistica_core
    raise NotImplementedError("E1: proprietatile sigmoidei")


# ---------------------------------------------------------------- Ex.2
def ex2_log_loss_manual(y_true, p):
    """E2. Implementeaza entropia incrucisata binara mediata de la zero (fara a apela
    cross_entropy_loss din nucleu). Tunde p in [1e-12, 1-1e-12]. Returneaza un float.
    """
    # TODO: -(1/n) sum [ y*log(p) + (1-y)*log(1-p) ]
    raise NotImplementedError("E2: log-loss de la zero")


# ---------------------------------------------------------------- Ex.3
def ex3_un_pas_gradient(X, y, w, lr):
    """E3. Un singur pas de coborare pe gradient pentru regresia logistica.
    Adauga interceptul cu add_bias, calculeaza p = sigmoid(Phi w), gradientul
    g = (1/n) Phi^T (p - y) si intoarce w_nou = w - lr * g. Returneaza vectorul w_nou.
    """
    # TODO
    raise NotImplementedError("E3: un pas de gradient")


# ---------------------------------------------------------------- Ex.4
def ex4_acuratete_test(seed=0):
    """E4. Pe make_link_usability_dataset(n_per_cond=120, seed=1), feature-urile FEATURES
    standardizate, antreneaza LogisticRegressionGD(lr=0.3, n_iter=4000, seed=seed) si
    intoarce acuratetea pe train (float). Asteptare: > 0.9.
    """
    # TODO
    raise NotImplementedError("E4: acuratete pe date reale-sintetice")


# ---------------------------------------------------------------- Ex.5
def ex5_prag_si_recall(prag):
    """E5. Pe acelasi set ca E4 (seed implicit 0 la model), antreneaza nucleul si intoarce
    RECALL-ul clasei pozitive (usable) pentru un PRAG de decizie dat pe probabilitate
    (foloseste predict(X, threshold=prag) si precision_recall_f1). Returneaza un float.
    Reflectie: un prag mai mic creste recall-ul (prinzi mai multe legaturi usable)?
    """
    # TODO
    raise NotImplementedError("E5: prag vs recall")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    s, comp = ex1_sigmoid_proprietati(0.0)
    ck("E1: sigmoid(0) = 0.5", abs(s - 0.5) < 1e-12)
    s2, comp2 = ex1_sigmoid_proprietati(1.7)
    ck("E1: sigmoid(z) = 1 - sigmoid(-z)", abs(s2 - comp2) < 1e-12)

    ck("E2: log-loss predictie perfecta ~ 0",
       ex2_log_loss_manual([1, 0, 1], [1 - 1e-9, 1e-9, 1 - 1e-9]) < 1e-6)
    ck("E2: log-loss la p=0.5 = ln 2",
       abs(ex2_log_loss_manual([1, 0], [0.5, 0.5]) - np.log(2.0)) < 1e-9)

    rng = np.random.default_rng(0)
    X = rng.standard_normal((50, 2))
    y = (X[:, 0] + X[:, 1] > 0).astype(int)
    w0 = np.zeros(3)
    w1 = ex3_un_pas_gradient(X, y, w0, lr=0.5)
    l0 = cross_entropy_loss(y, sigmoid(add_bias(X) @ w0))
    l1 = cross_entropy_loss(y, sigmoid(add_bias(X) @ w1))
    ck("E3: un pas de gradient scade pierderea", l1 < l0)

    ck("E4: acuratete pe train > 0.9", ex4_acuratete_test() > 0.9)

    r_lo = ex5_prag_si_recall(0.1)
    r_hi = ex5_prag_si_recall(0.9)
    ck("E5: prag mai mic -> recall >= prag mai mare", r_lo >= r_hi - 1e-9)

    print("\nTOATE EXERCITIILE M08 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
