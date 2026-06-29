#!/usr/bin/env python3
"""clustering_core.py -- nucleul M15, numpy pur (scikit-learn INTERZIS).

Invatare nesupervizata: gasim grupuri (cluster-e) in date FARA etichete. Doua
algoritme clasice, implementate de la zero:
  - k-means prin algoritmul Lloyd: atribuie fiecare punct la cel mai apropiat
    centroid, apoi muta fiecare centroid in media punctelor sale; repeta pana se
    stabilizeaza. Minimizeaza inertia (suma patratelor distantelor intra-cluster).
    Cu n_init reporniri (k-means++ pe seed-uri diferite) evitam minimele locale.
  - DBSCAN simplu, bazat pe densitate (eps, min_samples): grupuri de orice forma
    plus zgomot, fara sa fixam k dinainte.

Calitate fara etichete: scorul silhouette s = (b - a) / max(a, b), unde a e
distanta medie in propriul cluster si b e distanta medie la cel mai apropiat alt
cluster. s in [-1, 1]; mare = grupuri compacte si bine separate.

Determinism: orice aleator trece prin numpy.random.default_rng(seed).
_selftest() verifica:
  - pe 3 gaussiene bine separate, k-means recupereaza atribuirea adevarata (sub
    permutare de etichete, via acuratete maxima pe permutari);
  - inertia scade (sau ramane) la fiecare iteratie Lloyd (descrestere monotona);
  - silhouette in [-1, 1] si mare (> 0.5) pe cluster-e separate;
  - k-means determinist la aceeasi samanta.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python clustering_core.py
"""
import itertools
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml


# ============================================================ DISTANTE
def _pairwise_sq_dists(X, C):
    """Matrice n x k de distante EUCLIDIENE LA PATRAT intre punctele X (n x d) si
    centroizii C (k x d). ||x - c||^2 = ||x||^2 - 2 x.c + ||c||^2."""
    X = np.asarray(X, dtype=float)
    C = np.asarray(C, dtype=float)
    x2 = np.sum(X * X, axis=1).reshape(-1, 1)        # n x 1
    c2 = np.sum(C * C, axis=1).reshape(1, -1)        # 1 x k
    cross = X @ C.T                                   # n x k
    d2 = x2 - 2.0 * cross + c2
    return np.maximum(d2, 0.0)                        # taie negativele numerice


# ============================================================ K-MEANS++ INIT
def _kmeans_plusplus(X, k, rng):
    """Initializare k-means++: alege centroizi departati probabilistic, ca sa
    micsoreze sansa de minim local. Returneaza un array k x d de centroizi."""
    X = np.asarray(X, dtype=float)
    n = X.shape[0]
    first = int(rng.integers(n))
    centers = [X[first]]
    # d2[i] = distanta la patrat la cel mai apropiat centroid deja ales
    d2 = _pairwise_sq_dists(X, np.array(centers))[:, 0]
    for _ in range(1, k):
        total = d2.sum()
        if total <= 0.0:                              # toate punctele coincid
            idx = int(rng.integers(n))
        else:
            probs = d2 / total
            idx = int(rng.choice(n, p=probs))
        centers.append(X[idx])
        new_d2 = _pairwise_sq_dists(X, X[idx].reshape(1, -1))[:, 0]
        d2 = np.minimum(d2, new_d2)
    return np.array(centers)


# ============================================================ LLOYD (o repornire)
def _lloyd(X, k, rng, max_iter=100, tol=1e-10):
    """O singura rulare a algoritmului Lloyd, pornita din k-means++.

    Returneaza (labels, centers, inertia, inertia_hist), unde inertia_hist e
    inertia DUPA fiecare pas de actualizare (lista, monoton nedescrescatoare in
    sens invers -- vezi _selftest). Centroidul unui cluster gol e re-semanat pe
    punctul cel mai departat (evita cluster-e disparute)."""
    X = np.asarray(X, dtype=float)
    n = X.shape[0]
    centers = _kmeans_plusplus(X, k, rng)
    labels = np.zeros(n, dtype=int)
    inertia_hist = []
    prev_inertia = np.inf
    for _ in range(max_iter):
        # --- pasul de ATRIBUIRE: fiecare punct la cel mai apropiat centroid
        d2 = _pairwise_sq_dists(X, centers)
        labels = np.argmin(d2, axis=1)
        inertia = float(d2[np.arange(n), labels].sum())
        inertia_hist.append(inertia)
        # --- pasul de ACTUALIZARE: centroid = media punctelor atribuite
        new_centers = centers.copy()
        for j in range(k):
            mask = labels == j
            if np.any(mask):
                new_centers[j] = X[mask].mean(axis=0)
            else:
                # cluster gol: muta-l pe punctul cel mai prost servit acum
                far = int(np.argmax(d2[np.arange(n), labels]))
                new_centers[j] = X[far]
        centers = new_centers
        if prev_inertia - inertia <= tol:
            break
        prev_inertia = inertia
    # inertia finala cu centroizii ultimi (dupa actualizarea finala)
    d2 = _pairwise_sq_dists(X, centers)
    labels = np.argmin(d2, axis=1)
    inertia = float(d2[np.arange(n), labels].sum())
    return labels, centers, inertia, inertia_hist


# ============================================================ K-MEANS (n_init)
def kmeans(X, k, n_init=10, max_iter=100, seed=0):
    """k-means via Lloyd, cu n_init reporniri independente; pastreaza rularea cu
    inertia minima (evita minimele locale).

    Returneaza dict(labels, centers, inertia, inertia_hist). labels in 0..k-1,
    centers e k x d, inertia e suma patratelor intra-cluster a rularii pastrate.
    Determinist pentru (X, k, n_init, seed) fixe."""
    X = np.asarray(X, dtype=float)
    if not 1 <= k <= X.shape[0]:
        raise ValueError("k trebuie in [1, n], primit k=%d, n=%d" % (k, X.shape[0]))
    master = np.random.default_rng(seed)
    best = None
    for _ in range(n_init):
        sub = np.random.default_rng(int(master.integers(2**31 - 1)))
        labels, centers, inertia, hist = _lloyd(X, k, sub, max_iter=max_iter)
        if best is None or inertia < best["inertia"]:
            best = dict(labels=labels, centers=centers, inertia=inertia,
                        inertia_hist=hist)
    return best


# ============================================================ SILHOUETTE
def silhouette_samples(X, labels):
    """Scorul silhouette per punct. Pentru punctul i:
      a_i = distanta medie la celelalte puncte din propriul cluster,
      b_i = min pe celelalte cluster-e a distantei medii la acel cluster,
      s_i = (b_i - a_i) / max(a_i, b_i).
    Punctele dintr-un cluster cu un singur element primesc s = 0 (conventie).
    Returneaza un array de marime n."""
    X = np.asarray(X, dtype=float)
    labels = np.asarray(labels)
    n = X.shape[0]
    uniq = np.unique(labels)
    # distante euclidiene (nu la patrat) intre toate perechile
    D = np.sqrt(_pairwise_sq_dists(X, X))
    s = np.zeros(n)
    for i in range(n):
        own = labels == labels[i]
        own_count = int(own.sum())
        if own_count <= 1:
            s[i] = 0.0
            continue
        a = D[i, own].sum() / (own_count - 1)        # exclude pe i insusi
        b = np.inf
        for c in uniq:
            if c == labels[i]:
                continue
            mask = labels == c
            b = min(b, D[i, mask].mean())
        denom = max(a, b)
        s[i] = 0.0 if denom == 0 else (b - a) / denom
    return s


def silhouette_score(X, labels):
    """Scor silhouette mediu pe toate punctele, in [-1, 1]. Necesita >= 2
    cluster-e nevide; altfel ridica ValueError (silhouette nedefinit)."""
    labels = np.asarray(labels)
    if np.unique(labels).size < 2:
        raise ValueError("silhouette cere cel putin 2 cluster-e, primit %d"
                         % np.unique(labels).size)
    return float(silhouette_samples(X, labels).mean())


# ============================================================ DBSCAN (simplu)
def dbscan(X, eps, min_samples=5):
    """DBSCAN bazat pe densitate. Un punct e 'de baza' (core) daca are cel putin
    min_samples vecini (inclusiv el insusi) in raza eps. Cluster-ele cresc din
    punctele de baza prin vecinatati conectate; restul primesc eticheta -1 (zgomot).

    Returneaza un array de etichete (0..m-1 pentru cluster-e, -1 pentru zgomot).
    Implementare O(n^2) -- pentru cluster-e mici de demo, nu pentru productie."""
    X = np.asarray(X, dtype=float)
    n = X.shape[0]
    D = np.sqrt(_pairwise_sq_dists(X, X))
    neighbors = [np.where(D[i] <= eps)[0] for i in range(n)]
    labels = np.full(n, -1, dtype=int)               # -1 = nevizitat/zgomot
    visited = np.zeros(n, dtype=bool)
    cluster_id = 0
    for i in range(n):
        if visited[i]:
            continue
        visited[i] = True
        if neighbors[i].size < min_samples:
            continue                                  # ramane zgomot deocamdata
        # extinde un cluster nou pornind din i (BFS pe vecinatati)
        labels[i] = cluster_id
        queue = list(neighbors[i])
        while queue:
            j = queue.pop()
            if not visited[j]:
                visited[j] = True
                if neighbors[j].size >= min_samples:
                    queue.extend(neighbors[j].tolist())
            if labels[j] == -1:
                labels[j] = cluster_id
        cluster_id += 1
    return labels


# ============================================================ ACURATETE SUB PERMUTARE
def cluster_accuracy(y_true, labels):
    """Acuratete maxima a atribuirii pe toate permutarile de etichete de cluster
    fata de etichetele adevarate (clusterele nu au nume canonice). Practic doar
    pentru k mic in teste. Returneaza un float in [0, 1]."""
    y_true = np.asarray(y_true)
    labels = np.asarray(labels)
    classes = np.unique(y_true)
    clusters = np.unique(labels)
    best = 0.0
    for perm in itertools.permutations(classes):
        mapping = {c: perm[i] for i, c in enumerate(clusters)}
        mapped = np.array([mapping[l] for l in labels])
        best = max(best, float(np.mean(mapped == y_true)))
    return best


# ============================================================ DATE DE TEST
def _three_gaussians(n=60, seed=0, spread=0.45):
    """Trei gaussiene 2D bine separate (centre la coltul unui triunghi mare).
    Returneaza (X, y) cu y eticheta adevarata a cluster-ului -- folosita DOAR la
    evaluare, nu de algoritm."""
    g = np.random.default_rng(seed)
    centers = np.array([[0.0, 0.0], [6.0, 0.0], [3.0, 5.0]])
    X, y = [], []
    for j, c in enumerate(centers):
        X.append(g.normal(c, spread, size=(n, 2)))
        y.append(np.full(n, j))
    return np.vstack(X), np.concatenate(y)


# ============================================================ SELFTEST
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    X, y = _three_gaussians(n=80, seed=0)

    # 1) k-means recupereaza atribuirea adevarata (sub permutare de etichete)
    res = kmeans(X, k=3, n_init=10, seed=0)
    acc = cluster_accuracy(y, res["labels"])
    ck("kmeans: recupereaza 3 gaussiene separate (acc > 0.97)", acc > 0.97)
    ck("kmeans: 3 centroizi de dimensiunea 2", res["centers"].shape == (3, 2))
    ck("kmeans: etichete in 0..2", set(np.unique(res["labels"]).tolist()) <= {0, 1, 2})

    # 2) inertia scade (nu creste) la fiecare iteratie Lloyd
    _, _, _, hist = _lloyd(X, k=3, rng=np.random.default_rng(0))
    diffs = np.diff(np.array(hist))
    ck("lloyd: inertia monoton nedescrescatoare (diff <= tol)", np.all(diffs <= 1e-6))
    ck("lloyd: inertia finala < inertia initiala", hist[-1] <= hist[0] + 1e-9)

    # 3) silhouette in [-1, 1] si mare pe cluster-e separate
    s = silhouette_score(X, res["labels"])
    ck("silhouette: in [-1, 1]", -1.0 - 1e-9 <= s <= 1.0 + 1e-9)
    ck("silhouette: mare pe cluster-e separate (> 0.5)", s > 0.5)
    # silhouette scade cand fortam k gresit (k=2 amesteca doi din trei)
    res2 = kmeans(X, k=2, n_init=10, seed=0)
    s2 = silhouette_score(X, res2["labels"])
    ck("silhouette: k=3 (corect) > k=2 (gresit) ca silhouette", s > s2)

    # 4) determinism la aceeasi samanta
    a = kmeans(X, k=3, n_init=5, seed=7)
    b = kmeans(X, k=3, n_init=5, seed=7)
    ck("kmeans: determinist la aceeasi samanta (etichete egale)",
       np.array_equal(a["labels"], b["labels"]))
    ck("kmeans: determinist la aceeasi samanta (inertie egala)",
       abs(a["inertia"] - b["inertia"]) < 1e-9)

    # 5) silhouette cere >= 2 cluster-e
    try:
        silhouette_score(X, np.zeros(X.shape[0], dtype=int))
        raise AssertionError("FAIL: silhouette cu un singur cluster ar trebui sa ridice")
    except ValueError:
        ok += 1
        print("  [ok] silhouette: ridica ValueError cu un singur cluster")

    # 6) DBSCAN gaseste cele 3 grupuri dense pe aceleasi date
    db = dbscan(X, eps=1.0, min_samples=5)
    n_clusters = np.unique(db[db >= 0]).size
    ck("dbscan: gaseste 3 cluster-e dense", n_clusters == 3)

    print("\nTOATE VERIFICARILE clustering_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
