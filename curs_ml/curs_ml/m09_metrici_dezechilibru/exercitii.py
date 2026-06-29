#!/usr/bin/env python3
"""exercitii.py -- M09 Metrici, dezechilibru si calibrare (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste metrici_calibrare_core si utils.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from metrici_calibrare_core import (  # noqa: E402
    roc_auc, threshold_for_recall, expected_calibration_error,
    platt_fit, platt_predict,
)
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import confusion_matrix, precision_recall_f1  # noqa: E402


# ---------------------------------------------------------------- Ex.1
def ex1_acuratete_majoritar(y):
    """E1. Acuratetea clasificatorului care prezice MEREU clasa majoritara din y.
    Returneaza un float. (Vezi teorie.md sec. 3.1 -- baza fata de care compari.)
    """
    # TODO: afla clasa majoritara si masoara fractia in care y o egaleaza
    raise NotImplementedError("E1: acuratetea clasificatorului majoritar")


# ---------------------------------------------------------------- Ex.2
def ex2_auc_perechi(y, scor):
    """E2. AUC de la zero, prin numararea perechilor (pozitiv, negativ):
    +1 daca scor_poz > scor_neg, +0.5 la egalitate; imparte la n_poz*n_neg.
    NU folosi roc_auc. Returneaza un float.
    """
    # TODO: bucle duble pe pozitivi vs negativi
    raise NotImplementedError("E2: AUC prin numararea perechilor")


# ---------------------------------------------------------------- Ex.3
def ex3_precizie_recall(y, yp):
    """E3. Precizie si recall din matricea de confuzie (poti folosi
    confusion_matrix din utils). Returneaza (precizie, recall).
    """
    # TODO: ia TP, FP, FN si calculeaza precizie = TP/(TP+FP), recall = TP/(TP+FN)
    raise NotImplementedError("E3: precizie si recall de mana")


# ---------------------------------------------------------------- Ex.4
def ex4_prag_recall(y, scor, r_tinta):
    """E4. Cel mai mare prag care atinge recall >= r_tinta. Foloseste
    threshold_for_recall. Returneaza (prag, recall_obtinut).
    """
    # TODO
    raise NotImplementedError("E4: pragul pentru un recall-tinta")


# ---------------------------------------------------------------- helper
def _link_score():
    """Scor monoton simplu din feature-uri: cu cat p95 e mai mic, cu atat usable.
    (Dat -- il folosesti la Ex.5 si Ex.6.)"""
    df = make_link_usability_dataset(n_per_cond=120, seed=1)
    y = df["usable"].to_numpy(dtype=int)
    raw = -df["p95_ms"].to_numpy(dtype=float)
    return y, raw


# ---------------------------------------------------------------- Ex.5
def ex5_auc_link():
    """E5. AUC-ul scorului monoton (_link_score) fata de eticheta usable. Returneaza float.
    """
    # TODO: ia (y, raw) din _link_score() si intoarce roc_auc(y, raw)
    raise NotImplementedError("E5: AUC pe link-ul dezechilibrat")


# ---------------------------------------------------------------- Ex.6
def ex6_calibrare_platt():
    """E6. Aduce scorul brut din _link_score in [0,1] cu o sigmoida pe scorul
    standardizat, masoara ECE, potriveste platt_fit, masoara ECE dupa.
    Returneaza (ece_brut, ece_calibrat).
    """
    # TODO: prob_raw = sigmoid(zscore(raw)); ece inainte; platt_fit/platt_predict; ece dupa
    raise NotImplementedError("E6: calibrare cu Platt")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    y70 = np.r_[np.zeros(70), np.ones(30)].astype(int)
    ck("E1: acuratete majoritar = 0.70", abs(ex1_acuratete_majoritar(y70) - 0.70) < 1e-12)

    y_ex = np.array([1, 0, 1, 0])
    s_ex = np.array([0.9, 0.6, 0.4, 0.3])
    ck("E2: AUC perechi exemplu = 0.75", abs(ex2_auc_perechi(y_ex, s_ex) - 0.75) < 1e-12)
    rng = np.random.default_rng(3)
    yr = rng.integers(0, 2, 200)
    sr = rng.uniform(0, 1, 200)
    ck("E2: AUC perechi == roc_auc nucleu", abs(ex2_auc_perechi(yr, sr) - roc_auc(yr, sr)) < 1e-9)

    yt = np.array([1, 1, 1, 0, 0])
    yp = np.array([1, 1, 0, 1, 0])
    p, r = ex3_precizie_recall(yt, yp)
    ck("E3: precizie = 2/3", abs(p - 2.0 / 3.0) < 1e-12)
    ck("E3: recall = 2/3", abs(r - 2.0 / 3.0) < 1e-12)

    yb = np.r_[np.zeros(180), np.ones(20)].astype(int)
    sb = np.r_[rng.uniform(0.0, 0.7, 180), rng.uniform(0.3, 1.0, 20)]
    thr, rec = ex4_prag_recall(yb, sb, 0.9)
    ck("E4: recall obtinut >= tinta 0.9", rec >= 0.9 - 1e-9)
    _, rec_above, _ = precision_recall_f1(yb, (sb >= np.nextafter(thr, np.inf)).astype(int))
    ck("E4: prag e cel mai mare care atinge tinta (mai sus ar cadea sub)",
       rec_above < 0.9 or thr == max(sb))

    auc = ex5_auc_link()
    ck("E5: AUC link in (0.7, 1.0)", 0.7 < auc < 1.0)

    ece_raw, ece_cal = ex6_calibrare_platt()
    ck("E6: ECE dupa Platt <= ECE brut", ece_cal <= ece_raw + 1e-9)

    print("\nTOATE EXERCITIILE M09 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
