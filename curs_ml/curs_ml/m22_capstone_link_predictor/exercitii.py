#!/usr/bin/env python3
"""exercitii.py -- M22 CAPSTONE Predictor de link (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul link_predictor_core.

Datele sunt SINTETICE (semanate din C1/M via date_sar.py).

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from link_predictor_core import (  # noqa: E402
    LinkUsabilityPredictor, features_to_vector, FEATURE_NAMES,
)
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import train_test_split, accuracy  # noqa: E402


# ---------------------------------------------------------------- Ex.1
def ex1_features_to_vector(features):
    """E1. Asambleaza un dict {nume: valoare} in vectorul ordonat dupa FEATURE_NAMES.
    Foloseste features_to_vector din nucleu. Returneaza un numpy array 1D.
    """
    # TODO: cheama features_to_vector(features, FEATURE_NAMES)
    raise NotImplementedError("E1: dict de feature-uri -> vector ordonat")


# ---------------------------------------------------------------- Ex.2
def ex2_antreneaza_si_acuratete(seed=0):
    """E2. Antreneaza un LinkUsabilityPredictor pe TRAIN (split 30% test, seed 0) din
    make_link_usability_dataset(n_per_cond=200, seed=1) si intoarce acuratetea pe TEST.
    Returneaza un float. Asteptare: > 0.85.
    """
    # TODO: construieste X, y din FEATURE_NAMES + 'usable'; train_test_split;
    #       LinkUsabilityPredictor(...).train(...); accuracy(yte, model.predict_label(Xte))
    raise NotImplementedError("E2: antreneaza si masoara acuratetea pe TEST")


# ---------------------------------------------------------------- Ex.3
def ex3_bate_baza_triviala(seed=0):
    """E3. Pe acelasi split ca E2, intoarce (model_acc, base_acc) unde base_acc e
    acuratetea bazei triviale = a prezice mereu clasa MAJORITARA din TRAIN.
    Asteptare: model_acc > base_acc.
    """
    # TODO
    raise NotImplementedError("E3: compara modelul cu baza triviala")


# ---------------------------------------------------------------- Ex.4
def ex4_save_load_identic(tmp_path):
    """E4. Antreneaza un model (ca la E2), salveaza-l la tmp_path, incarca-l si
    intoarce True daca etichetele prezise pe TEST coincid EXACT intre model si copia
    incarcata (altfel False). Foloseste model.save / LinkUsabilityPredictor.load.
    """
    # TODO
    raise NotImplementedError("E4: save->load reproduce exact")


# ---------------------------------------------------------------- Ex.5
def ex5_predictie_consumabila(features):
    """E5. Impacheteaza predictia pentru un nod ROS subtire: antreneaza modelul (ca la
    E2), cheama model.predict(features) si intoarce dict-ul {usable: bool, prob: float}
    pe care l-ar publica nodul. prob rotunjit la 4 zecimale.
    """
    # TODO
    raise NotImplementedError("E5: predictie -> dict consumabil de link_adaptive")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    df = make_link_usability_dataset(n_per_cond=200, seed=1)
    sample = {k: float(df.iloc[0][k]) for k in FEATURE_NAMES}

    v = ex1_features_to_vector(sample)
    ck("E1: vector de lungimea FEATURE_NAMES, ordonat",
       v.shape == (len(FEATURE_NAMES),) and abs(v[0] - sample[FEATURE_NAMES[0]]) < 1e-12)

    acc = ex2_antreneaza_si_acuratete()
    ck("E2: acuratete pe TEST > 0.85", acc > 0.85)

    macc, bacc = ex3_bate_baza_triviala()
    ck("E3: model bate baza triviala", macc > bacc)

    here = os.path.dirname(os.path.abspath(__file__))
    tmp = os.path.join(here, "_ex_model.npz")
    same = ex4_save_load_identic(tmp)
    ck("E4: save->load reproduce exact etichetele", same is True)
    for p in (tmp, tmp + ".npz"):
        try:
            os.remove(p)
        except OSError:
            pass

    out = ex5_predictie_consumabila(sample)
    ck("E5: dict {usable: bool, prob: float}",
       isinstance(out, dict) and isinstance(out["usable"], bool)
       and 0.0 <= out["prob"] <= 1.0)

    print("\nTOATE EXERCITIILE M22 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
