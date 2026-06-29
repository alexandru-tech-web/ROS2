#!/usr/bin/env python3
"""exercitii.py -- stub-uri TODO pentru M00 (algebra liniara aplicata).

Completeaza functiile marcate cu TODO. Rulat ACUM, fisierul TREBUIE sa PICE clar
(asserturile cad pentru ca functiile intorc None / valori gresite). Pe masura ce
le rezolvi, asserturile trec. Solutiile complete sunt in solutii.py.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
(acum -> exit != 0; dupa rezolvare -> exit 0).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from algebra_liniara_core import covariance, norm, power_iteration  # noqa: E402
from date_sar import make_latency_dataset                          # noqa: E402


# ---------------------------------------------------------------- Exercitiul 1
def cosine_similarity(x, y):
    """E1. Similaritatea cosinus: cos(x, y) = <x, y> / (||x||_2 ||y||_2).

    Returneaza un float in [-1, 1]. Daca unul dintre vectori e ~0, returneaza 0.0.
    TODO: implementeaza folosind doar produs scalar si norma L2.
    """
    # TODO: inlocuieste linia de mai jos
    raise NotImplementedError("TODO E1: cosine_similarity")


# ---------------------------------------------------------------- Exercitiul 2
def project_onto_basis(x, Q):
    """E2. Proiectia lui x pe subspatiul generat de coloanele ORTONORMALE ale lui Q.

    Pentru Q cu Q^T Q = I, proiectia e p = Q (Q^T x). Returneaza (p, reziduu) unde
    reziduu = x - p si <reziduu, q_j> = 0 pentru orice coloana q_j a lui Q.
    TODO: implementeaza (foloseste produs matrice-vector).
    """
    # TODO
    raise NotImplementedError("TODO E2: project_onto_basis")


# ---------------------------------------------------------------- Exercitiul 3
def explained_variance_ratio(C):
    """E3. Fractia de varianta explicata de fiecare axa proprie a matricei
    simetrice C (covarianta).

    Pentru valorile proprii lambda_1 >= ... >= lambda_d >= 0, returneaza vectorul
    (lambda_i / sum_j lambda_j) sortat DESCRESCATOR. Suma trebuie sa fie ~1.
    TODO: foloseste numpy.linalg.eigh si sorteaza descrescator.
    """
    # TODO
    raise NotImplementedError("TODO E3: explained_variance_ratio")


# ---------------------------------------------------------------- Exercitiul 4
def dominant_axis_latency(seed=0):
    """E4. Pe date_sar.make_latency_dataset, intoarce (valoare_proprie_dominanta,
    vector_propriu_dominant) ale covariantei feature-urilor STANDARDIZATE
    ['loss_pct', 'base_lat_ms', 'jitter_ms', 'distance_m', 'rtt_ms'].

    Standardizeaza coloanele (z-score), calculeaza covarianta cu nucleul, apoi
    aplica power_iteration. Vectorul propriu trebuie normat (||v||_2 = 1).
    TODO.
    """
    # TODO
    raise NotImplementedError("TODO E4: dominant_axis_latency")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # E1
    ck("E1: cos(x, x) = 1", abs(cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) - 1.0) < 1e-9)
    ck("E1: cos vectori ortogonali = 0", abs(cosine_similarity([1.0, 0.0], [0.0, 5.0])) < 1e-9)
    ck("E1: cos antiparalel = -1", abs(cosine_similarity([1.0, 1.0], [-2.0, -2.0]) + 1.0) < 1e-9)

    # E2
    Q = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])   # baza ortonormala in R^3
    x = np.array([2.0, 3.0, 7.0])
    p, r = project_onto_basis(x, Q)
    ck("E2: proiectie pe e1,e2 = (2,3,0)", np.allclose(p, [2.0, 3.0, 0.0]))
    ck("E2: reziduu ortogonal pe baza", abs(float(r @ Q[:, 0])) < 1e-9 and abs(float(r @ Q[:, 1])) < 1e-9)

    # E3
    C = np.diag([4.0, 1.0, 0.0])
    evr = explained_variance_ratio(C)
    ck("E3: ratii sortate descrescator si suma 1",
       np.allclose(evr, [0.8, 0.2, 0.0]) and abs(float(np.sum(evr)) - 1.0) < 1e-9)

    # E4
    lam, v = dominant_axis_latency(seed=0)
    ck("E4: vector propriu normat", abs(norm(v, 2) - 1.0) < 1e-6)
    ck("E4: valoarea proprie pozitiva si rezonabila (>1)", lam > 1.0)

    print("\nTOATE EXERCITIILE M00 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("INCA DE REZOLVAT: %s" % e)
        sys.exit(1)
