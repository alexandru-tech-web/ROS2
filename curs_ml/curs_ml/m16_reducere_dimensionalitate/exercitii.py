#!/usr/bin/env python3
"""exercitii.py -- M16 Reducerea dimensionalitatii / PCA (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul pca_core.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from pca_core import PCA, _dominant_direction_data  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize  # noqa: E402

FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]


# ---------------------------------------------------------------- Ex.1
def ex1_centre_cov(X):
    """E1. Centreaza X (scade media pe coloane) si calculeaza covarianta de esantion
    C = Xc^T Xc / (n-1). Returneaza (Xc, C). NU folosi numpy.cov direct.
    """
    # TODO: scade media; formeaza C = Xc^T Xc / (n-1)
    raise NotImplementedError("E1: centrare si covarianta")


# ---------------------------------------------------------------- Ex.2
def ex2_var_dir(X, w):
    """E2. Varianta proiectiilor (w^T xc_i), cu w unitar. Foloseste ex1_centre_cov.
    Returneaza un float (= w^T C w).
    """
    # TODO
    raise NotImplementedError("E2: varianta de-a lungul unei directii")


# ---------------------------------------------------------------- Ex.3
def ex3_n_componente(ratii, prag):
    """E3. Numarul MINIM de componente a caror varianta CUMULATA atinge pragul.
    ratii e descrescator si insumeaza 1; prag in (0, 1]. Returneaza int.
    """
    # TODO
    raise NotImplementedError("E3: cate componente pentru un prag")


# ---------------------------------------------------------------- Ex.4
def ex4_pc1_dominanta(seed=1):
    """E4. Date 2D cu directie dominanta (_dominant_direction_data), potriveste PCA,
    intoarce (ratie_pc1, cos_aliniere) -- ratia de varianta a PC1 si |cos| intre PC1
    si directia generatoare.
    """
    # TODO
    raise NotImplementedError("E4: prima componenta a directiei dominante")


# ---------------------------------------------------------------- Ex.5
def ex5_var_2d():
    """E5. Pe make_latency_dataset(n_per_cond=150, seed=0), feature-uri standardizate,
    potriveste PCA si intoarce varianta explicata CUMULATA de primele 2 componente
    (float in (0, 1]).
    """
    # TODO
    raise NotImplementedError("E5: comprima latenta in 2D")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # E1: cele 4 puncte din teorie.md sec.7(b)
    X4 = np.array([[2.0, 0.0], [0.0, 2.0], [-2.0, 0.0], [0.0, -2.0]])
    Xc, C = ex1_centre_cov(X4)
    ck("E1: media centrata e zero", np.allclose(Xc.mean(axis=0), 0.0))
    ck("E1: C == [[8/3,0],[0,8/3]]", np.allclose(C, [[8 / 3, 0], [0, 8 / 3]]))

    # E2: cazul cu directie dominanta din teorie.md sec.7(d)
    Xd = np.array([[2.0, 0.0], [0.0, 6.0], [-2.0, 0.0], [0.0, -6.0]])
    ck("E2: varianta pe (0,1) = 24", abs(ex2_var_dir(Xd, np.array([0.0, 1.0])) - 24.0) < 1e-9)
    ck("E2: varianta pe (1,0) = 8/3", abs(ex2_var_dir(Xd, np.array([1.0, 0.0])) - 8 / 3) < 1e-9)

    # E3
    ck("E3: 3 componente pentru prag 0.9", ex3_n_componente([0.6, 0.25, 0.1, 0.05], 0.9) == 3)

    # E4
    ratie, cos = ex4_pc1_dominanta(seed=1)
    ck("E4: PC1 capteaza > 80% varianta", ratie > 0.8)
    ck("E4: PC1 aliniata cu directia (|cos| > 0.99)", cos > 0.99)

    # E5
    v2 = ex5_var_2d()
    ck("E5: varianta cumulata 2D in (0,1]", 0.0 < v2 <= 1.0)

    print("\nTOATE EXERCITIILE M16 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
