#!/usr/bin/env python3
"""exercitii.py -- M11 k-NN si SVM cu kernel (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul knn_svm_core.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from knn_svm_core import pegasos_svm, svm_predict, _linsep  # noqa: E402
from utils import standardize, accuracy  # noqa: E402


# ---------------------------------------------------------------- Ex.1
def ex1_dist_euclid(a, b):
    """E1. Distanta euclidiana intre vectorii a si b, fara numpy.linalg.
    Returneaza un float."""
    # TODO: sqrt(sum (a_i - b_i)^2)
    raise NotImplementedError("E1: distanta euclidiana")


# ---------------------------------------------------------------- Ex.2
def ex2_vot_knn(dists, labels, k):
    """E2. Vot majoritar pe cei k cei mai apropiati vecini. `dists` = distantele
    interogarii catre toate punctele de antrenare; `labels` = etichetele lor.
    La egalitate, eticheta cu indicele cel mai mic. NU folosi clasa KNN.
    Returneaza un int."""
    # TODO: argsort pe dists, ia primii k, voteaza cu numpy.bincount/argmax
    raise NotImplementedError("E2: votul k-NN")


# ---------------------------------------------------------------- Ex.3
def ex3_scara_strica_knn():
    """E3. Arata ca scara feature-urilor strica k-NN. Construieste 4 puncte de
    antrenare (2 din clasa 0, 2 din clasa 1) cu un feature informativ de scara
    mica si unul confound de scara mare, plus o interogare, asa incat k-NN(k=1) pe
    date BRUTE sa dea o eticheta, iar pe date STANDARDIZATE (utils.standardize)
    cealalta. Returneaza (eticheta_brut, eticheta_std)."""
    # TODO: alege X, y, q; calculeaza nn(k=1) pe brut si pe standardizat
    raise NotImplementedError("E3: scara strica k-NN")


# ---------------------------------------------------------------- Ex.4
def ex4_pas_pegasos(w, x, y, eta, lam):
    """E4. Un singur pas de actualizare Pegasos. Daca y*<w,x> < 1:
    w <- (1-eta*lam)w + eta*y*x ; altfel w <- (1-eta*lam)w. Returneaza noul w."""
    # TODO
    raise NotImplementedError("E4: pasul subgradient Pegasos")


# ---------------------------------------------------------------- Ex.5
def ex5_pegasos_acc(seed=0):
    """E5. Genereaza date liniar separabile (_linsep), antreneaza pegasos_svm si
    intoarce acuratetea de antrenare (float). Asteptare: > 0.95."""
    # TODO: _linsep -> pegasos_svm -> svm_predict -> accuracy
    raise NotImplementedError("E5: acuratetea Pegasos")


# ---------------------------------------------------------------- Ex.6
def ex6_rbf_gamma(x, z, gamma):
    """E6. Valoarea scalara a kernelului RBF exp(-gamma*||x-z||^2), fara
    knn_svm_core. Returneaza un float."""
    # TODO
    raise NotImplementedError("E6: kernel RBF scalar")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    ck("E1: ||(0,0)-(3,4)|| = 5", abs(ex1_dist_euclid([0, 0], [3, 4]) - 5.0) < 1e-12)

    Xt = np.array([[0.0, 0.0], [1.0, 0.0], [4.0, 4.0], [5.0, 4.0]])
    yt = np.array([0, 0, 1, 1])
    q = np.array([1.5, 0.5])
    dq = np.sum((Xt - q) ** 2, axis=1)
    ck("E2: vot k=1 -> clasa 0", ex2_vot_knn(dq, yt, 1) == 0)
    ck("E2: vot k=3 -> clasa 0", ex2_vot_knn(dq, yt, 3) == 0)

    eb, es = ex3_scara_strica_knn()
    ck("E3: brut != standardizat", eb != es)
    ck("E3: standardizat da clasa corecta 0", es == 0)

    w0 = np.zeros(2)
    x = np.array([1.0, 2.0])
    ck("E4: marja violata -> w = eta*y*x", np.allclose(ex4_pas_pegasos(w0, x, 1.0, 0.5, 0.0), 0.5 * x))
    ck("E4: marja respectata -> doar contractie",
       np.allclose(ex4_pas_pegasos(np.array([10.0, 0.0]), x, 1.0, 0.1, 0.5),
                   (1 - 0.1 * 0.5) * np.array([10.0, 0.0])))

    ck("E5: Pegasos acuratete > 0.95", ex5_pegasos_acc(0) > 0.95)

    ck("E6: rbf =1 cand x==z", abs(ex6_rbf_gamma([1.0, 2.0], [1.0, 2.0], 0.7) - 1.0) < 1e-12)
    ck("E6: rbf in (0,1) cand difera", 0.0 < ex6_rbf_gamma([0.0], [1.0], 0.5) < 1.0)
    ck("E6: gamma mare < gamma mic",
       ex6_rbf_gamma([0.0], [1.0], 5.0) < ex6_rbf_gamma([0.0], [1.0], 0.1))

    print("\nTOATE EXERCITIILE M11 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
