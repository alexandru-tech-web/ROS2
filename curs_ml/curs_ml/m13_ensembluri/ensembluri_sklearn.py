#!/usr/bin/env python3
"""ensembluri_sklearn.py -- validare incrucisata a nucleului M13 cu scikit-learn.

Verifica pe acelasi set ca ensemblurile noastre (bagging si gradient boosting)
sunt 'in regula': bat un singur ciot si stau in acelasi interval de acuratete ca
echivalentele din sklearn.ensemble (RandomForestClassifier, GradientBoostingClassifier).
Toleranta este LAXA -- nu reproducem implementarea, doar confirmam ca ordinul de
marime al acuratetei e acelasi (validare incrucisata, nu egalitate bit-cu-bit).

Iesire 0 daca potrivirile trec; daca sklearn lipseste, iesire 0 (nu e o eroare).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from ensembluri_core import (  # noqa: E402
    DecisionStump, BaggingClassifier, GradientBoostingClassifier, _toy_noisy,
)
from utils import accuracy  # noqa: E402

try:
    from sklearn.ensemble import (
        RandomForestClassifier, GradientBoostingClassifier as SkGB,
    )
    from sklearn.tree import DecisionTreeClassifier
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

    Xtr, ytr = _toy_noisy(n=500, seed=7)
    Xte, yte = _toy_noisy(n=500, seed=8)

    # referinta: un singur ciot (arbore de adancime 1)
    base = DecisionStump(task="clf").fit(Xtr, ytr)
    acc_base = accuracy(yte, base.predict(Xte).astype(int))
    sk_stump = DecisionTreeClassifier(max_depth=1, random_state=0).fit(Xtr, ytr)
    acc_sk_stump = accuracy(yte, sk_stump.predict(Xte))
    ck("ciotul nostru ~ DecisionTree(max_depth=1) sklearn (|d| < 0.07)",
       abs(acc_base - acc_sk_stump) < 0.07)

    # ---- bagging vs RandomForest
    bag = BaggingClassifier(n_estimators=61, seed=0).fit(Xtr, ytr)
    acc_bag = accuracy(yte, bag.predict(Xte))
    rf = RandomForestClassifier(n_estimators=61, max_depth=1, random_state=0).fit(Xtr, ytr)
    acc_rf = accuracy(yte, rf.predict(Xte))
    ck("bagging-ul nostru >= ciotul de baza", acc_bag >= acc_base - 0.02)
    ck("bagging-ul nostru ~ RandomForest sklearn (|d| < 0.10)", abs(acc_bag - acc_rf) < 0.10)

    # ---- gradient boosting vs sklearn GradientBoosting
    gb = GradientBoostingClassifier(n_estimators=80, learning_rate=0.3).fit(Xtr, ytr)
    acc_gb = accuracy(yte, gb.predict(Xte))
    sk_gb = SkGB(n_estimators=80, learning_rate=0.3, max_depth=1, random_state=0).fit(Xtr, ytr)
    acc_sk_gb = accuracy(yte, sk_gb.predict(Xte))
    ck("boosting-ul nostru >= ciotul de baza", acc_gb >= acc_base - 0.02)
    ck("boosting-ul nostru ~ GradientBoosting sklearn (|d| < 0.10)",
       abs(acc_gb - acc_sk_gb) < 0.10)

    print("\n  acuratete pe test:  ciot=%.3f  bagging=%.3f  boosting=%.3f" %
          (acc_base, acc_bag, acc_gb))
    print("  sklearn:            ciot=%.3f  RF=%.3f       GB=%.3f" %
          (acc_sk_stump, acc_rf, acc_sk_gb))
    print("\nVALIDARE INCRUCISATA M13 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
