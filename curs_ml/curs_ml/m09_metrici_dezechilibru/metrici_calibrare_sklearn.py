#!/usr/bin/env python3
"""metrici_calibrare_sklearn.py -- validare incrucisata a nucleului M09 cu scikit-learn.

Verifica pe ACELEASI date ca:
  - roc_auc al nucleului == sklearn.metrics.roc_auc_score (toleranta stransa);
  - precizia / recall / F1 ale clasei pozitive (din utils, prag dat) ==
    sklearn.metrics.precision_score / recall_score / f1_score;
  - precizia medie (AP) a nucleului ~ sklearn.metrics.average_precision_score.

Daca scikit-learn lipseste, iese 0 fara eroare (nu e o cerinta de mediu).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from metrici_calibrare_core import roc_auc, average_precision  # noqa: E402
from utils import precision_recall_f1  # noqa: E402

try:
    from sklearn.metrics import (
        roc_auc_score, average_precision_score,
        precision_score, recall_score, f1_score,
    )
except ImportError:
    print("[sklearn] indisponibil -- sar validarea incrucisata (nu e o eroare).")
    sys.exit(0)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    rng = np.random.default_rng(7)

    # date dezechilibrate cu scor informativ, dar zgomotos
    n_neg, n_pos = 400, 60
    y = np.r_[np.zeros(n_neg), np.ones(n_pos)].astype(int)
    s = np.r_[rng.normal(0.35, 0.20, n_neg), rng.normal(0.65, 0.20, n_pos)]
    s = np.clip(s, 0.0, 1.0)

    # 1) AUC-ROC nucleu == sklearn
    auc_core = roc_auc(y, s)
    auc_sk = float(roc_auc_score(y, s))
    ck("roc_auc nucleu == sklearn (|d| < 1e-9)", abs(auc_core - auc_sk) < 1e-9)

    # 2) precizia medie (AP) nucleu ~ sklearn
    ap_core = average_precision(y, s)
    ap_sk = float(average_precision_score(y, s))
    ck("average_precision nucleu ~ sklearn (|d| < 0.01)", abs(ap_core - ap_sk) < 0.01)

    # 3) precizie / recall / F1 la un prag dat == sklearn
    thr = 0.5
    yp = (s >= thr).astype(int)
    prec, rec, f1 = precision_recall_f1(y, yp)
    ck("precizie nucleu == sklearn", abs(prec - float(precision_score(y, yp, zero_division=0))) < 1e-12)
    ck("recall nucleu == sklearn", abs(rec - float(recall_score(y, yp, zero_division=0))) < 1e-12)
    ck("F1 nucleu == sklearn", abs(f1 - float(f1_score(y, yp, zero_division=0))) < 1e-12)

    print("\nVALIDARE INCRUCISATA M09 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
