#!/usr/bin/env python3
"""exercitii.py -- M14 Interpretabilitate (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul interpretabilitate_core.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from interpretabilitate_core import (  # noqa: E402
    permutation_importance, partial_dependence, shapley_linear,
    _linfit, _make_predict,
)
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import standardize, r2_score  # noqa: E402

FEATURES = ["p95_ms", "loss_frac", "jitter_ms", "base_lat_ms", "mw_zenoh", "distance_m"]


# ---------------------------------------------------------------- Ex.1
def ex1_shapley_manual(w, x, x_mean):
    """E1. Valoarea Shapley a unui model liniar, de mana (fara nucleu): pentru
    f(x)=w0 + sum_j w_j x_j, contributia feature-ului j este w_j*(x_j - E[x_j]).
    Returneaza un array (n_features,). NU folosi shapley_linear.
    """
    # TODO: implementeaza formula liniara element cu element
    raise NotImplementedError("E1: valoare Shapley liniara de mana")


# ---------------------------------------------------------------- Ex.2
def ex2_eficienta(w, x, x_mean, w0):
    """E2. Verifica proprietatea de eficienta: suma valorilor Shapley trebuie sa fie
    egala cu predictia minus baza. Returneaza (suma_phi, fx_minus_baza) ca tuplu de
    float, unde fx = w0 + w.x si baza = w0 + w.E[x]. Foloseste shapley_linear.
    """
    # TODO
    raise NotImplementedError("E2: proprietatea de eficienta")


# ---------------------------------------------------------------- Ex.3
def ex3_pdp_panta(coef):
    """E3. Pentru un model liniar f(x)=coef[0]*x0 + coef[1]*x1, panta profilului PDP
    pe feature 0 (pe un grid oarecare) trebuie sa fie chiar coef[0]. Construieste
    intern un model liniar (fara intercept), un X aleator (seed 0) si un grid, apoi
    intoarce panta PDP empirica pe feature 0 (un float). Foloseste partial_dependence.
    """
    # TODO: foloseste _make_predict(0.0, coef), un grid liniar, si raportul
    #       (pdp[-1]-pdp[0])/(grid[-1]-grid[0])
    raise NotImplementedError("E3: panta PDP = coeficientul")


# ---------------------------------------------------------------- Ex.4
def ex4_importanta_zgomot():
    """E4. Pe date unde DOAR feature 0 conteaza (feature 1 pur zgomot), antreneaza
    modelul liniar auxiliar si intoarce (imp0, imp1), importanta prin permutare a
    celor doua feature-uri. Asteptare: imp0 mare, imp1 ~0.
    Construieste intern: n=400, x0,x1 ~ uniform(-2,2) seed 0, y=3*x0+0.5+zgomot mic.
    """
    # TODO: _linfit -> _make_predict -> permutation_importance
    raise NotImplementedError("E4: importanta feature de zgomot ~0")


# ---------------------------------------------------------------- Ex.5
def ex5_top_feature_link():
    """E5. Pe make_link_usability_dataset(n_per_cond=200, seed=1), feature-uri
    standardizate, model liniar care prezice `usable`, intoarce NUMELE feature-ului
    cel mai important dupa importanta prin permutare (un string din FEATURES).
    Reflectie: ce variabila de link justifici in articol ca fiind decisiva?
    """
    # TODO
    raise NotImplementedError("E5: feature-ul de link cel mai important")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # E1: caz manual w=[2,-3], x=[1,4], E[x]=[0,5] -> phi=[2,3]
    phi = ex1_shapley_manual([2.0, -3.0], [1.0, 4.0], [0.0, 5.0])
    ck("E1: phi = [2, 3]", np.allclose(phi, [2.0, 3.0]))

    # E2: eficienta
    s, d = ex2_eficienta([1.5, -2.0, 0.7], [0.3, -0.4, 1.1], [0.0, 0.0, 0.0], 0.4)
    ck("E2: suma(phi) = f(x) - baza", abs(s - d) < 1e-12)

    # E3: panta PDP = coeficient
    ck("E3: panta PDP pe feature 0 ~ 2.0", abs(ex3_pdp_panta([2.0, -1.0]) - 2.0) < 1e-9)

    # E4: importanta de zgomot
    i0, i1 = ex4_importanta_zgomot()
    ck("E4: feature 0 important (> 0.5)", i0 > 0.5)
    ck("E4: feature de zgomot ~0 (< 0.02)", abs(i1) < 0.02)

    # E5: top feature de link
    top = ex5_top_feature_link()
    ck("E5: top feature de link este p95_ms", top == "p95_ms")

    print("\nTOATE EXERCITIILE M14 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
