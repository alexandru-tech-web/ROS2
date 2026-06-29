#!/usr/bin/env python3
"""knn_svm_sklearn.py -- validare incrucisata a nucleului M11 cu scikit-learn.

Verifica pe ACELEASI date sintetice:
  - k-NN-ul nucleului (KNN) ~ sklearn.neighbors.KNeighborsClassifier (aceleasi
    predictii / acuratete sub o toleranta laxa);
  - SVM-ul liniar Pegasos (pegasos_svm) ~ sklearn.svm.SVC(kernel='linear')
    (acuratete apropiata; ponderile difera fiindca obiectivele/scalarea difera).

Iesire 0 daca potrivirile trec. Daca sklearn lipseste, iese 0 (nu e o eroare).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from knn_svm_core import KNN, pegasos_svm, svm_predict, _two_clusters, _linsep  # noqa: E402
from utils import accuracy  # noqa: E402

try:
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.svm import SVC
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

    # 1) k-NN: aceleasi predictii ca sklearn pe doua cluster-e separate
    X, y = _two_clusters(n=60, seed=0)
    g = np.random.default_rng(11)
    Xte = np.vstack([g.normal([-3.0, -3.0], 0.6, size=(30, 2)),
                     g.normal([+3.0, +3.0], 0.6, size=(30, 2))])
    yte = np.concatenate([np.zeros(30, dtype=int), np.ones(30, dtype=int)])
    for k in (1, 3, 5):
        mine = KNN(k=k).fit(X, y).predict(Xte)
        skl = KNeighborsClassifier(n_neighbors=k).fit(X, y).predict(Xte)
        ck("k-NN k=%d: predictii identice cu sklearn" % k, np.array_equal(mine, skl))

    # 2) SVM liniar: acuratete apropiata de SVC(kernel='linear')
    Xl, yl = _linsep(n=120, seed=2)
    w = pegasos_svm(Xl, yl, lam=0.005, n_epoci=80, seed=0)
    acc_mine = accuracy(yl, svm_predict(Xl, w))
    svc = SVC(kernel="linear", C=1.0).fit(Xl, yl)
    acc_skl = accuracy(yl, svc.predict(Xl))
    ck("SVM liniar: acuratete Pegasos ~ SVC linear (|d| < 0.05)",
       abs(acc_mine - acc_skl) < 0.05)
    ck("SVM liniar: ambele separa aproape perfect (> 0.95)",
       acc_mine > 0.95 and acc_skl > 0.95)

    print("\nVALIDARE INCRUCISATA M11 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
