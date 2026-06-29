#!/usr/bin/env python3
"""solutii.py -- M09 Metrici, dezechilibru si calibrare (SOLUTIILE complete).

Ruleaza -> exit 0. Datele sunt SINTETICE (semanate din C1/M via date_sar.py).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from metrici_calibrare_core import (  # noqa: E402
    roc_auc, threshold_for_recall, expected_calibration_error,
    platt_fit, platt_predict,
)
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import confusion_matrix, precision_recall_f1  # noqa: E402


def ex1_acuratete_majoritar(y):
    y = np.asarray(y).astype(int).reshape(-1)
    majoritar = 1 if y.mean() >= 0.5 else 0
    return float(np.mean(y == majoritar))


def ex2_auc_perechi(y, scor):
    y = np.asarray(y).astype(int).reshape(-1)
    s = np.asarray(scor, dtype=float).reshape(-1)
    pos = s[y == 1]
    neg = s[y == 0]
    if pos.size == 0 or neg.size == 0:
        return 0.5
    wins = 0.0
    for sp in pos:
        for sn in neg:
            if sp > sn:
                wins += 1.0
            elif sp == sn:
                wins += 0.5
    return float(wins / (pos.size * neg.size))


def ex3_precizie_recall(y, yp):
    cm = confusion_matrix(y, yp)
    tp, fp, fn = cm[1, 1], cm[0, 1], cm[1, 0]
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return float(prec), float(rec)


def ex4_prag_recall(y, scor, r_tinta):
    return threshold_for_recall(y, scor, r_tinta)


def _link_score():
    """Scor monoton simplu din feature-uri: cu cat p95 e mai mic, cu atat usable."""
    df = make_link_usability_dataset(n_per_cond=120, seed=1)
    y = df["usable"].to_numpy(dtype=int)
    raw = -df["p95_ms"].to_numpy(dtype=float)  # monoton (mai mic p95 -> mai usable)
    return y, raw


def ex5_auc_link():
    y, raw = _link_score()
    return float(roc_auc(y, raw))


def ex6_calibrare_platt():
    y, raw = _link_score()
    # aducem scorul brut in [0,1] cu o sigmoida pe scorul standardizat
    z = (raw - raw.mean()) / (raw.std() + 1e-12)
    prob_raw = 1.0 / (1.0 + np.exp(-z))
    ece_raw = expected_calibration_error(y, prob_raw, n_bins=10)
    params = platt_fit(prob_raw, y, lr=0.5, n_iter=4000, seed=0)
    prob_cal = platt_predict(prob_raw, params)
    ece_cal = expected_calibration_error(y, prob_cal, n_bins=10)
    return float(ece_raw), float(ece_cal)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    y70 = np.r_[np.zeros(70), np.ones(30)].astype(int)
    ck("E1: acuratete majoritar = 0.70", abs(ex1_acuratete_majoritar(y70) - 0.70) < 1e-12)

    y_ex = np.array([1, 0, 1, 0])
    s_ex = np.array([0.9, 0.6, 0.4, 0.3])
    ck("E2: AUC perechi exemplu = 0.75", abs(ex2_auc_perechi(y_ex, s_ex) - 0.75) < 1e-12)
    rng = np.random.default_rng(3)
    yr = rng.integers(0, 2, 200)
    sr = rng.uniform(0, 1, 200)
    ck("E2: AUC perechi == roc_auc nucleu", abs(ex2_auc_perechi(yr, sr) - roc_auc(yr, sr)) < 1e-9)

    yt = np.array([1, 1, 1, 0, 0])
    yp = np.array([1, 1, 0, 1, 0])
    p, r = ex3_precizie_recall(yt, yp)
    ck("E3: precizie = 2/3", abs(p - 2.0 / 3.0) < 1e-12)
    ck("E3: recall = 2/3", abs(r - 2.0 / 3.0) < 1e-12)

    yb = np.r_[np.zeros(180), np.ones(20)].astype(int)
    sb = np.r_[rng.uniform(0.0, 0.7, 180), rng.uniform(0.3, 1.0, 20)]
    thr, rec = ex4_prag_recall(yb, sb, 0.9)
    ck("E4: recall obtinut >= tinta 0.9", rec >= 0.9 - 1e-9)
    _, rec_above, _ = precision_recall_f1(yb, (sb >= np.nextafter(thr, np.inf)).astype(int))
    ck("E4: prag e cel mai mare care atinge tinta (mai sus ar cadea sub)",
       rec_above < 0.9 or thr == max(sb))

    auc = ex5_auc_link()
    ck("E5: AUC link in (0.7, 1.0)", 0.7 < auc < 1.0)

    ece_raw, ece_cal = ex6_calibrare_platt()
    ck("E6: ECE dupa Platt <= ECE brut", ece_cal <= ece_raw + 1e-9)

    print("\nTOATE SOLUTIILE M09 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
