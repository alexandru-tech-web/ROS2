#!/usr/bin/env python3
"""exercitii.py -- stub-uri TODO pentru M04 (Date si feature engineering).

Completeaza functiile marcate cu TODO. RULAT ACUM trebuie sa PICE clar (un
assert va esua), pana cand rezolvi exercitiile. Solutiile complete stau in
solutii.py (nu te uita acolo inainte sa incerci).

Verificare:
  /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
  -> acum: iesire non-0 (PICA), cu mesaj clar. Dupa rezolvare: iesire 0.

Refoloseste nucleul din date_features_core (nu reimplementa de la zero ce exista,
decat daca exercitiul cere explicit).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from date_features_core import (  # noqa: E402
    fit_one_hot, transform_one_hot,
    fit_mean_imputer, transform_mean_imputer,
    polynomial_features, iqr_outlier_mask,
)
from date_sar import make_latency_dataset  # noqa: E402
from utils import train_test_split, standardize  # noqa: E402


# --------------------------------------------------------------------------
# Ex.1 -- one-hot manual pe o coloana cu 3 categorii.
# Returneaza matricea indicator (n, 3) pentru etichetele date, in ordinea
# alfabetica a categoriilor unice. Foloseste nucleul.
def ex1_one_hot(labels):
    # TODO: invata vocabularul cu fit_one_hot si transforma cu transform_one_hot
    raise NotImplementedError("TODO ex1: one-hot pe `labels`")


# --------------------------------------------------------------------------
# Ex.2 -- imputare FARA scurgere.
# Date Xtr, Xte (cu NaN), invata media pe TRAIN si umple AMBELE seturi cu ea.
# Returneaza (Xtr_imputat, Xte_imputat).
def ex2_impute_no_leak(Xtr, Xte):
    # TODO: fit_mean_imputer pe Xtr; transform_mean_imputer pe Xtr si pe Xte
    raise NotImplementedError("TODO ex2: imputare cu media de pe TRAIN")


# --------------------------------------------------------------------------
# Ex.3 -- numarul de coloane polinomiale.
# Returneaza numarul de coloane produse de un polinom de grad `degree` pe `p`
# feature-uri, FARA bias. (Poti folosi formula sau polynomial_features.)
def ex3_n_poly_cols(p, degree):
    # TODO: calculeaza numarul de coloane (ex: p=4, degree=2 -> 14)
    raise NotImplementedError("TODO ex3: numar de coloane polinomiale")


# --------------------------------------------------------------------------
# Ex.4 -- fractia de outlieri IQR pe rtt_ms.
# Pe make_latency_dataset(n_per_cond=200, seed=0), returneaza fractia de randuri
# marcate ca outlier de regula IQR (k=1.5) pe coloana rtt_ms.
def ex4_outlier_fraction():
    # TODO: ia rtt_ms din dataset, aplica iqr_outlier_mask, intoarce media mastii
    raise NotImplementedError("TODO ex4: fractie outlieri IQR pe rtt_ms")


# --------------------------------------------------------------------------
# Ex.5 -- pipeline mic fara scurgere (one-hot + z-score) pe primele N randuri.
# Date un df de latenta, split 75/25 (seed=0), construieste matricea de feature:
# one-hot pe middleware + z-score pe ['loss_pct','distance_m'] cu stat de pe TRAIN.
# Returneaza (F_tr, F_te) cu coloanele in ordinea [one-hot..., z(loss_pct), z(distance_m)].
def ex5_pipeline(df):
    # TODO:
    #  1. split pe indici cu train_test_split (test_frac=0.25, seed=0)
    #  2. one-hot pe middleware: fit pe TRAIN, transform pe ambele
    #  3. standardize pe ['loss_pct','distance_m'] cu stat de pe TRAIN
    #  4. column_stack [one-hot, z-numeric] pentru fiecare set
    raise NotImplementedError("TODO ex5: pipeline one-hot + z-score fara scurgere")


# ==========================================================================
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # ex1
    M = ex1_one_hot(["b", "a", "c", "a"])
    ck("ex1: forma (4,3)", np.shape(M) == (4, 3))
    ck("ex1: un singur 1 per rand", np.array_equal(np.sum(M, axis=1), np.ones(4)))
    ck("ex1: rand 0 ('b') aprinde coloana 1", M[0, 1] == 1.0)

    # ex2
    Xtr = np.array([[1.0, 10.0], [3.0, np.nan], [np.nan, 20.0]])
    Xte = np.array([[np.nan, np.nan]])
    Atr, Ate = ex2_impute_no_leak(Xtr, Xte)
    ck("ex2: fara NaN dupa imputare", not np.isnan(Atr).any() and not np.isnan(Ate).any())
    ck("ex2: media TRAIN col0 = 2.0", abs(Atr[2, 0] - 2.0) < 1e-9)
    ck("ex2: TEST umplut cu media TRAIN (col0=2.0)", abs(Ate[0, 0] - 2.0) < 1e-9)

    # ex3
    ck("ex3: p=4,degree=2 -> 14", ex3_n_poly_cols(4, 2) == 14)
    ck("ex3: p=2,degree=3 -> 9", ex3_n_poly_cols(2, 3) == 9)

    # ex4
    frac = ex4_outlier_fraction()
    ck("ex4: fractie outlieri in (0, 0.5)", 0.0 < frac < 0.5)

    # ex5
    df = make_latency_dataset(n_per_cond=50, seed=0)
    F_tr, F_te = ex5_pipeline(df)
    ck("ex5: 4 coloane (2 one-hot + 2 z)", F_tr.shape[1] == 4)
    ck("ex5: train+test = tot setul", F_tr.shape[0] + F_te.shape[0] == len(df))
    ck("ex5: media z pe TRAIN ~ 0", np.allclose(F_tr[:, 2:].mean(axis=0), 0, atol=1e-9))

    print("\nTOATE EXERCITIILE M04 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
