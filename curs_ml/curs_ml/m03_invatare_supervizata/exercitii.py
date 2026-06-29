#!/usr/bin/env python3
"""exercitii.py -- M03 Cadrul invatarii supervizate (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO si sterge `raise NotImplementedError`.
Rulat ACUM, fisierul TREBUIE sa PICE (exit != 0) -- exact comportamentul corect
inainte de rezolvare. Dupa ce rezolvi, aserturile trec si _check() iese cu 0.
Solutiile complete sunt in solutii.py (separat).

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from invatare_supervizata_core import (  # noqa: E402
    squared_loss, hinge_loss, logistic_loss, sigmoid, fit_poly, predict_poly,
    bias_variance_decomposition,
)


# ---------------------------------------------------------------- Exercitiul 1
def ex1_risc_empiric_patratic(y_true, y_pred):
    """E1. Calculeaza riscul empiric patratic R_emp = (1/n) sum (y_i - p_i)^2.

    Foloseste squared_loss din nucleu. Returneaza un float.
    """
    # TODO: aplica squared_loss si mediaza
    raise NotImplementedError("E1: implementeaza riscul empiric patratic")


# ---------------------------------------------------------------- Exercitiul 2
def ex2_eroare_clasificator_prag(scores, y_true, threshold=0.0):
    """E2. Pentru scoruri reale si etichete {0,1}, prezice 1 daca score > threshold,
    apoi returneaza eroarea 0-1 (fractia de clasificari gresite).

    Returneaza un float in [0, 1].
    """
    # TODO: aplica pragul, compara cu y_true, intoarce fractia gresita
    raise NotImplementedError("E2: implementeaza eroarea 0-1 cu prag")


# ---------------------------------------------------------------- Exercitiul 3
def ex3_compara_surogate(score):
    """E3. Pentru un singur scor (clasa pozitiva y=+1 in hinge, y=1 in logistica),
    returneaza tuple (hinge, logistica) -- valorile celor doua surogate.

    Foloseste hinge_loss (y=+1) si logistic_loss (y=1). Returneaza (float, float).
    """
    # TODO: evalueaza cele doua pierderi la acest scor
    raise NotImplementedError("E3: implementeaza compararea surogatelor")


# ---------------------------------------------------------------- Exercitiul 4
def ex4_grad_optim_biasvar(f_true, x_grid, sigma, n_train, degrees,
                           n_datasets=400, seed=0):
    """E4. Ruleaza descompunerea bias-varianta pentru fiecare grad din `degrees`
    si returneaza gradul cu EROAREA TOTALA estimata minima (punctul de echilibru).

    Foloseste bias_variance_decomposition din nucleu (camp 'total'). Returneaza int.
    """
    # TODO: pentru fiecare grad calculeaza 'total', alege argmin
    raise NotImplementedError("E4: implementeaza alegerea gradului optim")


# ---------------------------------------------------------------- Exercitiul 5
def ex5_efect_n_train_variance(f_true, x_grid, sigma, degree, n_trains,
                               n_datasets=400, seed=0):
    """E5. Pentru un grad FIX si o lista de marimi de set de antrenare `n_trains`,
    returneaza lista variantelor (camp 'variance') in aceeasi ordine.

    Scop: arata ca varianta SCADE cand creste n_train (mai multe date stabilizeaza).
    Returneaza o lista de float, len == len(n_trains).
    """
    # TODO: pentru fiecare n_train ruleaza descompunerea si culege 'variance'
    raise NotImplementedError("E5: implementeaza efectul lui n_train asupra variantei")


# ---------------------------------------------------------------- Exercitiul 6
def ex6_polinom_underfit_overfit(f_true, sigma, n_train, seed=0):
    """E6. Antreneaza pe UN set de antrenare doua polinoame: grad 1 (rigid) si
    grad 12 (flexibil). Pe un grid dens [-0.9, 0.9], returneaza tuple
    (rmse_grad1, rmse_grad12) fata de f_true (FARA zgomot, deci eroarea de potrivire
    a formei). Asteptare tipica la N mic: grad 1 sub-invata (rmse mare din bias),
    grad 12 supra-invata (rmse mare din varianta).

    Returneaza (float, float).
    """
    # TODO: genereaza un set, potriveste grad 1 si grad 12, evalueaza pe grid
    raise NotImplementedError("E6: implementeaza comparatia underfit vs overfit")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # E1
    r = ex1_risc_empiric_patratic([3.0, 0.0, -2.0], [1.0, 0.0, 1.0])
    ck("E1: R_emp patratic = 13/3", abs(r - 13.0 / 3.0) < 1e-12)

    # E2
    e = ex2_eroare_clasificator_prag([0.4, -0.2, 1.1, -0.9], [1, 0, 1, 1], threshold=0.0)
    # praguri: [1,0,1,0] vs [1,0,1,1] -> 1 gresit din 4 = 0.25
    ck("E2: eroare 0-1 cu prag = 0.25", abs(e - 0.25) < 1e-12)

    # E3
    h, lg = ex3_compara_surogate(0.0)
    ck("E3: hinge(0)=1, logistica(0)=log2",
       abs(h - 1.0) < 1e-12 and abs(lg - np.log(2)) < 1e-12)

    # E4 / E5 / E6 pe un proces comun
    def f_true(x):
        return np.sin(1.5 * np.pi * np.asarray(x, dtype=float))

    x_grid = np.linspace(-0.9, 0.9, 25)
    sigma = 0.2

    best = ex4_grad_optim_biasvar(f_true, x_grid, sigma, n_train=20,
                                  degrees=list(range(0, 10)), n_datasets=400, seed=5)
    ck("E4: gradul optim e interior (1 <= d* <= 8)", 1 <= best <= 8)

    variances = ex5_efect_n_train_variance(f_true, x_grid, sigma, degree=6,
                                           n_trains=[15, 40, 120], n_datasets=300, seed=5)
    ck("E5: varianta scade cu n_train",
       variances[0] > variances[1] > variances[2])

    rmse1, rmse12 = ex6_polinom_underfit_overfit(f_true, sigma, n_train=12, seed=5)
    ck("E6: grad 1 si grad 12 dau rmse pozitiv", rmse1 > 0 and rmse12 > 0)

    print("\nTOATE EXERCITIILE M03 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
