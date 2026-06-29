#!/usr/bin/env python3
"""arbori_decizie_sklearn.py -- validare incrucisata a nucleului M12 cu scikit-learn.

Verifica:
  - impuritatile gini/entropy ale nucleului == cele calculate de sklearn pe
    aceleasi distributii (formula identica);
  - arborele nostru CART si sklearn.tree.DecisionTreeClassifier (criteriu si
    adancime egale) dau ACEEASI acuratete sub toleranta pe acelasi set separabil;
  - feature-ul ales la radacina coincide pe date separabile pe o axa.

Daca sklearn lipseste, iesire 0 (nu e o eroare).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from arbori_decizie_core import gini, entropy, best_split, DecisionTreeCart  # noqa: E402
from utils import accuracy  # noqa: E402

try:
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

    # 1) impuritatile coincid cu definitiile sklearn (gini si entropie/log2)
    y = np.array([0, 0, 0, 1, 1])
    p = np.bincount(y) / y.size
    gini_ref = 1.0 - np.sum(p ** 2)
    ent_ref = -np.sum(p[p > 0] * np.log2(p[p > 0]))
    ck("gini nucleu == 1 - sum p^2", abs(gini(y) - gini_ref) < 1e-12)
    ck("entropy nucleu == -sum p log2 p", abs(entropy(y) - ent_ref) < 1e-12)

    # 2) acuratete egala cu sklearn pe acelasi set separabil, aceeasi adancime/criteriu
    rng = np.random.default_rng(0)
    X = rng.uniform(-1, 1, size=(400, 2))
    yc = ((X[:, 0] > 0.0) & (X[:, 1] > 0.0)).astype(int)
    for crit in ("gini", "entropy"):
        mine = DecisionTreeCart(max_depth=3, criterion=crit).fit(X, yc)
        skl = DecisionTreeClassifier(max_depth=3, criterion=crit,
                                     random_state=0).fit(X, yc)
        acc_mine = accuracy(yc, mine.predict(X))
        acc_skl = accuracy(yc, skl.predict(X))
        ck("acuratete nucleu ~ sklearn (criterion=%s, |d| < 0.02)" % crit,
           abs(acc_mine - acc_skl) < 0.02)
        ck("ambele clasifica aproape perfect (criterion=%s)" % crit,
           acc_mine > 0.98 and acc_skl > 0.98)

    # 3) feature-ul de la radacina coincide pe date separabile pe o axa
    f0 = rng.uniform(-1, 1, 300)
    f1 = rng.uniform(-1, 1, 300)
    ya = (f1 > 0).astype(int)                 # doar coloana 1 conteaza
    Xa = np.column_stack([f0, f1])
    root_mine = best_split(Xa, ya, "gini")["feature"]
    skl = DecisionTreeClassifier(max_depth=1, criterion="gini",
                                 random_state=0).fit(Xa, ya)
    root_skl = int(skl.tree_.feature[0])
    ck("feature radacina nucleu == sklearn (coloana 1)",
       root_mine == 1 and root_skl == 1)

    print("\nVALIDARE INCRUCISATA M12 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
