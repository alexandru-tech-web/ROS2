#!/usr/bin/env python3
"""solutii.py -- M15 Clustering (SOLUTIILE complete). Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from clustering_core import (  # noqa: E402
    kmeans, silhouette_score, cluster_accuracy, _three_gaussians,
    _pairwise_sq_dists,
)
from date_sar import make_channel_dataset  # noqa: E402
from utils import standardize  # noqa: E402

FEATURES = ["distance_m", "path_loss_db", "margin_db", "delivered_frac"]


def ex1_atribuire_lloyd(X, centers):
    d2 = _pairwise_sq_dists(X, centers)
    return np.argmin(d2, axis=1)


def ex2_actualizare_centroizi(X, labels, k):
    X = np.asarray(X, dtype=float)
    labels = np.asarray(labels)
    return np.array([X[labels == j].mean(axis=0) for j in range(k)])


def ex3_inertie(X, labels, centers):
    X = np.asarray(X, dtype=float)
    centers = np.asarray(centers, dtype=float)
    labels = np.asarray(labels)
    diff = X - centers[labels]
    return float(np.sum(diff * diff))


def ex4_recupereaza_gaussiene():
    X, y = _three_gaussians(n=80, seed=1)
    res = kmeans(X, k=3, n_init=10, seed=0)
    return cluster_accuracy(y, res["labels"])


def ex5_alege_k():
    df = make_channel_dataset("urban_rubble", seed=2, n=300)
    Xs, _, _, _ = standardize(df[FEATURES].to_numpy(dtype=float))
    ks = [2, 3, 4, 5]
    sils = [silhouette_score(Xs, kmeans(Xs, k=k, n_init=10, seed=0)["labels"]) for k in ks]
    return int(ks[int(np.argmax(sils))])


def ex6_scara_conteaza():
    g = np.random.default_rng(0)
    n = 150
    small = np.concatenate([g.normal(0.15, 0.03, n), g.normal(0.85, 0.03, n)])
    big = g.normal(80.0, 25.0, 2 * n)                 # zgomot mare care domina distanta
    y = np.concatenate([np.zeros(n, dtype=int), np.ones(n, dtype=int)])
    X = np.column_stack([small, big])
    acc_brut = cluster_accuracy(y, kmeans(X, k=2, n_init=10, seed=0)["labels"])
    Xs, _, _, _ = standardize(X)
    acc_std = cluster_accuracy(y, kmeans(Xs, k=2, n_init=10, seed=0)["labels"])
    return float(acc_brut), float(acc_std)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    Xs = np.array([[0.0], [1.0], [9.0], [10.0]])
    C = np.array([[0.0], [10.0]])
    ck("E1: atribuire la cel mai apropiat centroid",
       ex1_atribuire_lloyd(Xs, C).tolist() == [0, 0, 1, 1])
    C2 = ex2_actualizare_centroizi(Xs, np.array([0, 0, 1, 1]), 2)
    ck("E2: centroizi = media clusterelor", np.allclose(np.sort(C2.ravel()), [0.5, 9.5]))
    ck("E3: inertia = 1.0 pe cazul de mana",
       abs(ex3_inertie(Xs, np.array([0, 0, 1, 1]), C2) - 1.0) < 1e-9)
    ck("E4: recupereaza 3 gaussiene (acc > 0.97)", ex4_recupereaza_gaussiene() > 0.97)
    ck("E5: k ales = 3 pe regimurile de canal", ex5_alege_k() == 3)
    ab, asd = ex6_scara_conteaza()
    ck("E6: standardizarea reda structura (acc_std > acc_brut)", asd > ab)

    print("\nTOATE SOLUTIILE M15 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
