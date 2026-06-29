#!/usr/bin/env python3
"""exercitii.py -- M02 Optimizare pentru ML. Stub-uri TODO.

Completeaza fiecare functie marcata cu TODO. Rulat ACUM (nerezolvat), scriptul
TREBUIE sa PICE clar (iesire non-zero) la primul assert. Pe masura ce rezolvi,
asserturile trec. Solutiile complete sunt in solutii.py (NU te uita pana incerci).

Ruleaza:
  /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from optimizare_core import quadratic_grad, quadratic_solution, quadratic_value

TODO = "TODO: rezolva acest exercitiu"


# ---------------------------------------------------------------- Exercitiul 1
def ex1_grad_numeric(f, w, h=1e-5):
    """Ex1. Implementeaza gradientul prin diferente finite CENTRATE.

    Formula: d f / d w_i ~ (f(w + h e_i) - f(w - h e_i)) / (2h).
    Returneaza un vector numpy de aceeasi forma cu w.
    """
    # TODO: construieste gradientul coordonata cu coordonata cu diferente centrate
    raise NotImplementedError(TODO)


# ---------------------------------------------------------------- Exercitiul 2
def ex2_gd(grad, w0, eta, n_iter):
    """Ex2. Implementeaza coborarea pe gradient (batch GD).

    Itereaza w <- w - eta * grad(w) de n_iter ori. Returneaza w final.
    """
    # TODO: bucla de coborare pe gradient
    raise NotImplementedError(TODO)


# ---------------------------------------------------------------- Exercitiul 3
def ex3_momentum(grad, w0, eta, mu, n_iter):
    """Ex3. Implementeaza coborarea cu moment (heavy-ball).

    v <- mu*v - eta*grad(w) ; w <- w + v. v initial = 0. Returneaza w final.
    """
    # TODO: bucla cu moment
    raise NotImplementedError(TODO)


# ---------------------------------------------------------------- Exercitiul 4
def ex4_best_step(A):
    """Ex4. Pasul optim al GD pe o patratica cu Hessiana A (SPD).

    Returneaza eta = 2 / (lambda_max(A) + lambda_min(A)).
    Foloseste numpy.linalg.eigvalsh.
    """
    # TODO: calculeaza pasul optim din valorile proprii ale lui A
    raise NotImplementedError(TODO)


# ---------------------------------------------------------------- Exercitiul 5
def ex5_early_stopping(grad, value_val, w0, eta, n_iter, patience):
    """Ex5. GD cu oprire timpurie (early stopping) pe o pierdere de validare.

    La fiecare iteratie evalueaza value_val(w) (pierdere pe validare). Tine minte
    cel mai bun w (pierdere minima). Daca pierderea nu se imbunatateste timp de
    `patience` iteratii consecutive, opreste si returneaza CEL MAI BUN w gasit
    (nu ultimul). Returneaza (w_best, best_val, n_iteratii_efectuate).
    """
    # TODO: implementeaza oprirea timpurie cu rabdare (patience)
    raise NotImplementedError(TODO)


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # banc de proba: patratica SPD
    A = np.array([[3.0, 1.0], [1.0, 2.0]])
    b = np.array([1.0, -2.0])
    w_star = quadratic_solution(A, b)
    f = lambda w: quadratic_value(w, A, b)
    grad = lambda w: quadratic_grad(w, A, b)

    # Ex1
    g_num = ex1_grad_numeric(f, np.array([0.5, -0.3]))
    ck("ex1: diferente finite == gradient analitic",
       np.linalg.norm(g_num - grad(np.array([0.5, -0.3]))) < 1e-5)

    # Ex2
    eta = ex4_best_step(A)
    w_gd = ex2_gd(grad, np.array([5.0, 5.0]), eta, 300)
    ck("ex2: GD converge la w* = A^-1 b", np.allclose(w_gd, w_star, atol=1e-6))

    # Ex3
    w_mom = ex3_momentum(grad, np.array([5.0, 5.0]), 0.05, 0.9, 400)
    ck("ex3: momentum converge la w*", np.allclose(w_mom, w_star, atol=1e-5))

    # Ex4
    ev = np.linalg.eigvalsh(A)
    ck("ex4: pas optim = 2/(lmax+lmin)", abs(ex4_best_step(A) - 2.0 / (ev[0] + ev[-1])) < 1e-12)

    # Ex5: pierderea de validare scade apoi creste (supra-invatare simulata)
    #   value_val(w) = ||w - c||^2 ; dar 'antrenarea' trage spre alt punct d != c,
    #   deci validarea atinge un minim apoi creste -> oprirea timpurie il prinde.
    c = np.array([1.0, 1.0])      # optimul de validare
    d = np.array([4.0, -2.0])     # optimul de antrenare (diferit -> supra-invatare)
    grad_tr = lambda w: 2.0 * (w - d)
    val = lambda w: float(np.sum((w - c) ** 2))
    w_best, best_val, n_done = ex5_early_stopping(grad_tr, val, np.zeros(2),
                                                  eta=0.05, n_iter=500, patience=10)
    ck("ex5: oprirea timpurie returneaza w mai aproape de optimul de validare",
       np.linalg.norm(w_best - c) < np.linalg.norm(d - c))
    ck("ex5: s-a oprit inainte de n_iter (a declansat patience)", n_done < 500)
    ck("ex5: best_val e pierderea la w_best", abs(best_val - val(w_best)) < 1e-9)

    print("\nTOATE EXERCITIILE M02 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("\nINCA NEREZOLVAT (asta e normal inainte sa rezolvi): %s" % e)
        sys.exit(1)
