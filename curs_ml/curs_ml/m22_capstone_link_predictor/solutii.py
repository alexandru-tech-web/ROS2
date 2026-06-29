#!/usr/bin/env python3
"""solutii.py -- M22 CAPSTONE Predictor de link (SOLUTIILE complete). Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from link_predictor_core import (  # noqa: E402
    LinkUsabilityPredictor, features_to_vector, FEATURE_NAMES,
)
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import train_test_split, accuracy  # noqa: E402


def _split(seed=0):
    df = make_link_usability_dataset(n_per_cond=200, seed=1)
    X = df[FEATURE_NAMES].to_numpy(dtype=float)
    y = df["usable"].to_numpy(dtype=int)
    return train_test_split(X, y, test_frac=0.30, seed=seed)


def ex1_features_to_vector(features):
    return features_to_vector(features, FEATURE_NAMES)


def ex2_antreneaza_si_acuratete(seed=0):
    Xtr, Xte, ytr, yte = _split(seed)
    model = LinkUsabilityPredictor(lr=0.2, n_iter=3000, seed=0).train(Xtr, ytr)
    return float(accuracy(yte, model.predict_label(Xte)))


def ex3_bate_baza_triviala(seed=0):
    Xtr, Xte, ytr, yte = _split(seed)
    model = LinkUsabilityPredictor(lr=0.2, n_iter=3000, seed=0).train(Xtr, ytr)
    model_acc = float(accuracy(yte, model.predict_label(Xte)))
    maj = int(round(ytr.mean()))
    base_acc = float(accuracy(yte, np.full_like(yte, maj)))
    return model_acc, base_acc


def ex4_save_load_identic(tmp_path):
    Xtr, Xte, ytr, yte = _split(0)
    model = LinkUsabilityPredictor(lr=0.2, n_iter=3000, seed=0).train(Xtr, ytr)
    model.save(tmp_path)
    loaded = LinkUsabilityPredictor.load(tmp_path)
    return bool(np.array_equal(model.predict_label(Xte), loaded.predict_label(Xte)))


def ex5_predictie_consumabila(features):
    Xtr, _, ytr, _ = _split(0)
    model = LinkUsabilityPredictor(lr=0.2, n_iter=3000, seed=0).train(Xtr, ytr)
    label, prob = model.predict(features)
    return {"usable": bool(label), "prob": round(float(prob), 4)}


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
    ck("E1: vector ordonat de lungimea FEATURE_NAMES",
       v.shape == (len(FEATURE_NAMES),) and abs(v[0] - sample[FEATURE_NAMES[0]]) < 1e-12)

    ck("E2: acuratete pe TEST > 0.85", ex2_antreneaza_si_acuratete() > 0.85)

    macc, bacc = ex3_bate_baza_triviala()
    ck("E3: model bate baza triviala", macc > bacc)

    here = os.path.dirname(os.path.abspath(__file__))
    tmp = os.path.join(here, "_sol_model.npz")
    ck("E4: save->load reproduce exact", ex4_save_load_identic(tmp) is True)
    for p in (tmp, tmp + ".npz"):
        try:
            os.remove(p)
        except OSError:
            pass

    out = ex5_predictie_consumabila(sample)
    ck("E5: dict {usable: bool, prob: float}",
       isinstance(out, dict) and isinstance(out["usable"], bool) and 0.0 <= out["prob"] <= 1.0)

    print("\nTOATE SOLUTIILE M22 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
