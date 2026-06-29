#!/usr/bin/env python3
"""solutii.py -- M11 k-NN si SVM cu kernel (SOLUTIILE complete). Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from knn_svm_core import pegasos_svm, svm_predict, _linsep  # noqa: E402
from utils import standardize, accuracy  # noqa: E402


def ex1_dist_euclid(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return float(np.sqrt(np.sum((a - b) ** 2)))


def ex2_vot_knn(dists, labels, k):
    dists = np.asarray(dists, dtype=float)
    labels = np.asarray(labels).astype(int)
    nn = np.argsort(dists, kind="stable")[:k]
    voturi = np.bincount(labels[nn], minlength=int(labels.max()) + 1)
    return int(np.argmax(voturi))


def ex3_scara_strica_knn():
    # feature0: informativ, scara mica (~0.1); feature1: confound, scara mare (~1000)
    X = np.array([
        [0.10, 300.0],   # class0
        [0.15, 700.0],   # class0
        [0.90, 360.0],   # class1 (feature1 aproape de interogare -> deruteaza brutul)
        [0.95, 800.0],   # class1
    ], dtype=float)
    y = np.array([0, 0, 1, 1])
    q = np.array([0.12, 355.0])   # feature0 spune clasa 0; feature1 e langa idx2 (clasa 1)

    # k=1 pe date BRUTE: feature1 domina distanta -> alege clasa 1 (gresit)
    d_brut = np.sum((X - q) ** 2, axis=1)
    et_brut = int(y[np.argmin(d_brut)])

    # k=1 pe date STANDARDIZATE: feature0 conteaza la fel -> alege clasa 0 (corect)
    Xs, qs, _, _ = standardize(X, q.reshape(1, -1))
    d_std = np.sum((Xs - qs[0]) ** 2, axis=1)
    et_std = int(y[np.argmin(d_std)])
    return et_brut, et_std


def ex4_pas_pegasos(w, x, y, eta, lam):
    w = np.asarray(w, dtype=float)
    x = np.asarray(x, dtype=float)
    if y * (w @ x) < 1.0:
        return (1.0 - eta * lam) * w + eta * y * x
    return (1.0 - eta * lam) * w


def ex5_pegasos_acc(seed=0):
    X, y = _linsep(n=80, seed=seed + 1)
    w = pegasos_svm(X, y, lam=0.01, n_epoci=50, seed=seed)
    return float(accuracy(y, svm_predict(X, w)))


def ex6_rbf_gamma(x, z, gamma):
    x = np.asarray(x, dtype=float)
    z = np.asarray(z, dtype=float)
    return float(np.exp(-gamma * np.sum((x - z) ** 2)))


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    ck("E1: ||(0,0)-(3,4)|| = 5", abs(ex1_dist_euclid([0, 0], [3, 4]) - 5.0) < 1e-12)

    # exemplul din teorie: 4 puncte, interogare (1.5,0.5)
    Xt = np.array([[0.0, 0.0], [1.0, 0.0], [4.0, 4.0], [5.0, 4.0]])
    yt = np.array([0, 0, 1, 1])
    q = np.array([1.5, 0.5])
    dq = np.sum((Xt - q) ** 2, axis=1)
    ck("E2: vot k=1 -> clasa 0", ex2_vot_knn(dq, yt, 1) == 0)
    ck("E2: vot k=3 -> clasa 0", ex2_vot_knn(dq, yt, 3) == 0)

    eb, es = ex3_scara_strica_knn()
    ck("E3: scara strica k-NN (brut != standardizat)", eb != es)
    ck("E3: standardizat da clasa corecta 0", es == 0)

    w0 = np.zeros(2)
    x = np.array([1.0, 2.0])
    w_viol = ex4_pas_pegasos(w0, x, 1.0, 0.5, 0.0)
    ck("E4: marja violata muta w spre y*x", np.allclose(w_viol, 0.5 * x))
    w_ok = ex4_pas_pegasos(np.array([10.0, 0.0]), x, 1.0, 0.1, 0.5)
    ck("E4: marja respectata = doar contractie", np.allclose(w_ok, (1 - 0.1 * 0.5) * np.array([10.0, 0.0])))

    ck("E5: Pegasos acuratete > 0.95", ex5_pegasos_acc(0) > 0.95)

    ck("E6: rbf =1 cand x==z", abs(ex6_rbf_gamma([1.0, 2.0], [1.0, 2.0], 0.7) - 1.0) < 1e-12)
    v = ex6_rbf_gamma([0.0], [1.0], 0.5)
    ck("E6: rbf in (0,1) cand difera", 0.0 < v < 1.0)
    ck("E6: gamma mare < gamma mic (nucleu mai ingust)",
       ex6_rbf_gamma([0.0], [1.0], 5.0) < ex6_rbf_gamma([0.0], [1.0], 0.1))

    print("\nTOATE SOLUTIILE M11 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
