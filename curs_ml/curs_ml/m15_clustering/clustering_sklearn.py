#!/usr/bin/env python3
"""clustering_sklearn.py -- validare incrucisata a nucleului M15 cu scikit-learn.

Verifica pe ACELEASI date sintetice:
  - k-means-ul nucleului (kmeans) ~ sklearn.cluster.KMeans: aceeasi partitie (sub
    permutare de etichete, via cluster_accuracy) si inertie comparabila;
  - silhouette_score-ul nucleului ~ sklearn.metrics.silhouette_score (toleranta
    stransa -- aceeasi formula).

Iesire 0 daca potrivirile trec. Daca sklearn lipseste, iese 0 (nu e o eroare).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from clustering_core import (  # noqa: E402
    kmeans, silhouette_score, cluster_accuracy, _three_gaussians,
)

try:
    from sklearn.cluster import KMeans as SkKMeans
    from sklearn.metrics import silhouette_score as sk_silhouette
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

    X, y = _three_gaussians(n=100, seed=0)

    # 1) aceeasi partitie ca sklearn (sub permutare de etichete)
    mine = kmeans(X, k=3, n_init=10, seed=0)
    sk = SkKMeans(n_clusters=3, n_init=10, random_state=0).fit(X)
    agree = cluster_accuracy(sk.labels_, mine["labels"])
    ck("kmeans: aceeasi partitie ca sklearn (acord > 0.97)", agree > 0.97)

    # 2) inertie comparabila (acelasi minim global pe date separate)
    rel = abs(mine["inertia"] - sk.inertia_) / sk.inertia_
    ck("kmeans: inertie ~ sklearn (eroare relativa < 0.02)", rel < 0.02)

    # 3) silhouette ~ sklearn pe ACEEASI partitie (formula identica)
    s_mine = silhouette_score(X, mine["labels"])
    s_sk = float(sk_silhouette(X, mine["labels"]))
    ck("silhouette: nucleu ~ sklearn (|d| < 1e-6)", abs(s_mine - s_sk) < 1e-6)

    print("\nVALIDARE INCRUCISATA M15 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
