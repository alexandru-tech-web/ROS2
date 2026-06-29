#!/usr/bin/env python3
"""exercitii.py -- M15 Clustering (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul clustering_core.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from clustering_core import (  # noqa: E402
    kmeans, silhouette_score, cluster_accuracy, _three_gaussians,
)
from date_sar import make_channel_dataset  # noqa: E402
from utils import standardize  # noqa: E402

FEATURES = ["distance_m", "path_loss_db", "margin_db", "delivered_frac"]


# ---------------------------------------------------------------- Ex.1
def ex1_atribuire_lloyd(X, centers):
    """E1. Pasul de ATRIBUIRE din Lloyd, de mana: pentru fiecare rand din X (n x d),
    intoarce indicele celui mai apropiat centroid din centers (k x d), folosind
    distanta euclidiana. Returneaza un array de int de marime n. NU folosi kmeans.
    """
    # TODO: calculeaza distantele la fiecare centroid si ia argmin pe axa centroizilor
    raise NotImplementedError("E1: pasul de atribuire Lloyd")


# ---------------------------------------------------------------- Ex.2
def ex2_actualizare_centroizi(X, labels, k):
    """E2. Pasul de ACTUALIZARE din Lloyd: noul centroid al fiecarui cluster e MEDIA
    punctelor atribuite. Returneaza un array k x d. Presupune fiecare cluster nevid.
    """
    # TODO: pentru fiecare j in 0..k-1, media randurilor cu labels == j
    raise NotImplementedError("E2: pasul de actualizare a centroizilor")


# ---------------------------------------------------------------- Ex.3
def ex3_inertie(X, labels, centers):
    """E3. Inertia (suma patratelor intra-cluster): suma pe toate punctele a
    distantei la PATRAT pana la centroidul propriului cluster. Returneaza un float.
    """
    # TODO
    raise NotImplementedError("E3: inertia")


# ---------------------------------------------------------------- Ex.4
def ex4_recupereaza_gaussiene():
    """E4. Pe _three_gaussians(n=80, seed=1), ruleaza kmeans(k=3, n_init=10, seed=0)
    si intoarce acuratetea atribuirii fata de etichetele adevarate (cluster_accuracy).
    Returneaza un float. Asteptare: > 0.97 (cluster-e bine separate).
    """
    # TODO
    raise NotImplementedError("E4: recuperarea gaussienelor")


# ---------------------------------------------------------------- Ex.5
def ex5_alege_k():
    """E5. Pe make_channel_dataset('urban_rubble', seed=2, n=300), feature-uri
    STANDARDIZATE, ruleaza kmeans pentru k in {2,3,4,5} si intoarce k-ul cu cel mai
    mare silhouette. Returneaza un int. (Vezi demo_sil: standardizarea conteaza.)
    """
    # TODO
    raise NotImplementedError("E5: alegerea lui k prin silhouette")


# ---------------------------------------------------------------- Ex.6
def ex6_scara_conteaza():
    """E6. Arata ca SCARA conteaza. Construieste un caz sintetic cu doua grupuri a
    cate 150 de puncte (default_rng(0)): structura ADEVARATA traieste intr-un feature
    'mic' (~0.15 vs ~0.85, sigma 0.03), iar un al doilea feature 'mare' e zgomot pur
    de amplitudine mare (normal(80, 25)). k-means cu distanta euclidiana e dominat de
    feature-ul mare daca nu standardizezi.
    Ruleaza kmeans(k=2, n_init=10, seed=0) si intoarce (acc_brut, acc_std), unde acc e
    cluster_accuracy fata de etichetele adevarate:
      (a) pe feature-uri BRUTE, (b) pe feature-uri STANDARDIZATE.
    Asteptare: acc_std > acc_brut (standardizarea reda structura ascunsa de scara).
    NOTA: silhouette poate fi inselator de mare pe date brute -- masoara separarea in
    spatiul brut, dominat de zgomot; de aceea comparam cu ADEVARUL, nu silhouette.
    """
    # TODO: construieste X (small, big), standardizeaza, compara acuratetea
    raise NotImplementedError("E6: scara feature-urilor conteaza")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # E1: atribuire pe un caz mic 1D, calculabil de mana
    Xs = np.array([[0.0], [1.0], [9.0], [10.0]])
    C = np.array([[0.0], [10.0]])
    lab = ex1_atribuire_lloyd(Xs, C)
    ck("E1: atribuire la cel mai apropiat centroid", lab.tolist() == [0, 0, 1, 1])

    # E2: actualizare = media; centroizii noi sunt 0.5 si 9.5
    C2 = ex2_actualizare_centroizi(Xs, np.array([0, 0, 1, 1]), 2)
    ck("E2: centroizi = media clusterelor", np.allclose(np.sort(C2.ravel()), [0.5, 9.5]))

    # E3: inertia cu centroizii 0.5, 9.5 = 4 * 0.25 = 1.0
    inert = ex3_inertie(Xs, np.array([0, 0, 1, 1]), C2)
    ck("E3: inertia = 1.0 pe cazul de mana", abs(inert - 1.0) < 1e-9)

    ck("E4: recupereaza 3 gaussiene (acc > 0.97)", ex4_recupereaza_gaussiene() > 0.97)

    ck("E5: k ales = 3 pe regimurile de canal", ex5_alege_k() == 3)

    ab, asd = ex6_scara_conteaza()
    ck("E6: standardizarea reda structura (acc_std > acc_brut)", asd > ab)

    print("\nTOATE EXERCITIILE M15 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
