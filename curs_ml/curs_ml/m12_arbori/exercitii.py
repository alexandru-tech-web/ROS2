#!/usr/bin/env python3
"""exercitii.py -- M12 Arbori de decizie (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul arbori_decizie_core.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from arbori_decizie_core import (  # noqa: E402
    gini, entropy, best_split, DecisionTreeCart,
)
from date_sar import make_mission_outcome_dataset  # noqa: E402
from utils import train_test_split, accuracy  # noqa: E402

FEATURES = ["delivered_frac", "p95_ms", "n_drones"]


# ---------------------------------------------------------------- Ex.1
def ex1_gini_de_mana(counts):
    """E1. Calculeaza Gini de la zero dintr-un vector de numarari pe clase
    (ex. [3, 1] = 3 din clasa 0 si 1 din clasa 1), FARA a folosi gini().
    Formula: 1 - sum_c p_c^2, cu p_c = count_c / total. Returneaza un float.
    """
    # TODO: transforma numararile in proportii si aplica 1 - sum p^2
    raise NotImplementedError("E1: Gini de mana din numarari")


# ---------------------------------------------------------------- Ex.2
def ex2_castig_split(y_parinte, y_stanga, y_dreapta):
    """E2. Reducerea de impuritate (castigul) Gini a unui split dat ca trei
    vectori de etichete: parintele si cei doi copii. Foloseste gini() din nucleu.
    Castig = G(parinte) - (n_st/n) G(stanga) - (n_dr/n) G(dreapta). Float.
    """
    # TODO: pondereaza impuritatile copiilor cu fractiile lor si scade din parinte
    raise NotImplementedError("E2: castigul unui split")


# ---------------------------------------------------------------- Ex.3
def ex3_prag_optim(X, y):
    """E3. Pe un set 1D (X are o coloana), gaseste pragul ales de best_split (Gini).
    Returneaza un float (threshold). Foloseste best_split.
    """
    # TODO: apeleaza best_split si intoarce campul threshold
    raise NotImplementedError("E3: pragul optim")


# ---------------------------------------------------------------- Ex.4
def ex4_acuratete_adancime(max_depth):
    """E4. Antreneaza un arbore cu max_depth dat pe mission_complete (split fix
    seed=0, test_frac=0.25) si intoarce (acc_train, acc_test). Foloseste
    make_mission_outcome_dataset(n=500, seed=3), FEATURES, train_test_split, accuracy.
    """
    # TODO: construieste X,y; imparte; antreneaza DecisionTreeCart; raporteaza acc
    raise NotImplementedError("E4: acuratete vs adancime")


# ---------------------------------------------------------------- Ex.5
def ex5_supra_invatare():
    """E5. Arata supra-invatarea: compara golul (acc_train - acc_test) la un arbore
    ADANC (max_depth=None) fata de un CIOT (max_depth=1), pe mission_complete.
    Returneaza (gol_adanc, gol_ciot). Asteptare: gol_adanc >= gol_ciot.
    Refoloseste ex4_acuratete_adancime.
    """
    # TODO: cheama ex4 cu None si cu 1; calculeaza fiecare gol train-test
    raise NotImplementedError("E5: golul de supra-invatare")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # E1: [2,2] -> 0.5 ; [4,0] -> 0.0 ; [3,1] -> 0.375
    ck("E1: Gini [2,2] = 0.5", abs(ex1_gini_de_mana([2, 2]) - 0.5) < 1e-12)
    ck("E1: Gini [4,0] = 0.0", abs(ex1_gini_de_mana([4, 0]) - 0.0) < 1e-12)
    ck("E1: Gini [3,1] = 0.375", abs(ex1_gini_de_mana([3, 1]) - 0.375) < 1e-12)

    # E2: parinte 50/50, copii puri -> castig = 0.5
    g = ex2_castig_split([0, 0, 1, 1], [0, 0], [1, 1])
    ck("E2: castig split pur = 0.5", abs(g - 0.5) < 1e-12)

    # E3: x in {1,2,3,4,5,6}, y=0 pentru x<=3 -> prag 3.5
    X = np.array([[1.0], [2.0], [3.0], [4.0], [5.0], [6.0]])
    y = np.array([0, 0, 0, 1, 1, 1])
    ck("E3: prag optim = 3.5", abs(ex3_prag_optim(X, y) - 3.5) < 1e-9)

    # E4: arbore mic clasifica peste hazard (test > 0.5)
    acc_tr, acc_te = ex4_acuratete_adancime(3)
    ck("E4: acuratete test > 0.5 la max_depth=3", acc_te > 0.5)
    ck("E4: train >= test (de obicei)", acc_tr >= acc_te - 1e-9)

    # E5: arborele adanc supra-invata mai mult decat ciotul
    gol_adanc, gol_ciot = ex5_supra_invatare()
    ck("E5: golul adanc >= golul ciotului", gol_adanc >= gol_ciot - 1e-9)

    print("\nTOATE EXERCITIILE M12 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
