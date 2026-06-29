#!/usr/bin/env python3
"""solutii.py -- M12 Arbori de decizie (SOLUTIILE complete). Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from arbori_decizie_core import (  # noqa: E402
    gini, best_split, DecisionTreeCart,
)
from date_sar import make_mission_outcome_dataset  # noqa: E402
from utils import train_test_split, accuracy  # noqa: E402

FEATURES = ["delivered_frac", "p95_ms", "n_drones"]


def ex1_gini_de_mana(counts):
    c = np.asarray(counts, dtype=float)
    total = c.sum()
    if total == 0:
        return 0.0
    p = c / total
    return float(1.0 - np.sum(p ** 2))


def ex2_castig_split(y_parinte, y_stanga, y_dreapta):
    yp = np.asarray(y_parinte).astype(int)
    yl = np.asarray(y_stanga).astype(int)
    yr = np.asarray(y_dreapta).astype(int)
    n = yp.size
    child = (yl.size / n) * gini(yl) + (yr.size / n) * gini(yr)
    return float(gini(yp) - child)


def ex3_prag_optim(X, y):
    return float(best_split(X, y, "gini")["threshold"])


def ex4_acuratete_adancime(max_depth):
    df = make_mission_outcome_dataset(n=500, seed=3)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["mission_complete"].to_numpy(dtype=int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_frac=0.25, seed=0)
    tree = DecisionTreeCart(max_depth=max_depth, min_samples_split=2).fit(Xtr, ytr)
    return float(accuracy(ytr, tree.predict(Xtr))), float(accuracy(yte, tree.predict(Xte)))


def ex5_supra_invatare():
    tr_a, te_a = ex4_acuratete_adancime(None)
    tr_c, te_c = ex4_acuratete_adancime(1)
    return float(tr_a - te_a), float(tr_c - te_c)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    ck("E1: Gini [2,2] = 0.5", abs(ex1_gini_de_mana([2, 2]) - 0.5) < 1e-12)
    ck("E1: Gini [4,0] = 0.0", abs(ex1_gini_de_mana([4, 0]) - 0.0) < 1e-12)
    ck("E1: Gini [3,1] = 0.375", abs(ex1_gini_de_mana([3, 1]) - 0.375) < 1e-12)

    g = ex2_castig_split([0, 0, 1, 1], [0, 0], [1, 1])
    ck("E2: castig split pur = 0.5", abs(g - 0.5) < 1e-12)

    X = np.array([[1.0], [2.0], [3.0], [4.0], [5.0], [6.0]])
    y = np.array([0, 0, 0, 1, 1, 1])
    ck("E3: prag optim = 3.5", abs(ex3_prag_optim(X, y) - 3.5) < 1e-9)

    acc_tr, acc_te = ex4_acuratete_adancime(3)
    ck("E4: acuratete test > 0.5", acc_te > 0.5)
    ck("E4: train >= test", acc_tr >= acc_te - 1e-9)

    gol_adanc, gol_ciot = ex5_supra_invatare()
    ck("E5: golul adanc >= golul ciotului", gol_adanc >= gol_ciot - 1e-9)

    print("\nTOATE SOLUTIILE M12 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
