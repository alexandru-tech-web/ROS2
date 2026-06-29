#!/usr/bin/env python3
"""knn_svm_core.py -- nucleul M11, numpy pur (scikit-learn INTERZIS).

Trei piese construite de la zero:
  (a) k-NN: clasificator pe vecini, distante euclidiene + vot majoritar pe k vecini;
  (b) SVM liniar prin Pegasos: subgradient stocastic pe pierderea hinge cu
      regularizare L2 (w <- (1 - eta*lam) w + eta*y*x doar cand y*<w,x> < 1);
  (c) kernel RBF: k(x, z) = exp(-gamma * ||x - z||^2), pentru granite neliniare.

Notatie (vezi M00/M02): X are forma (n, d), etichetele y in {-1, +1} pentru SVM si
in {0, 1, ...} pentru k-NN. Distanta euclidiana ||x - z|| = sqrt(sum_i (x_i-z_i)^2).

Determinism: ordinea de baleiere a lui Pegasos trece prin
numpy.random.default_rng(seed). _selftest() verifica:
  - k-NN cu k=1 clasifica PERFECT punctele de antrenare (vecinul cel mai apropiat e el insusi);
  - k-NN clasifica corect doua cluster-e bine separate;
  - Pegasos separa date liniar separabile (acuratete > 0.95);
  - kernelul RBF e simetric, =1 pe diagonala si in (0, 1] in afara ei.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python knn_svm_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import accuracy  # noqa: E402


# ============================================================ DISTANTE
def pairwise_sq_dists(A, B):
    """Matrice (na, nb) cu distantele euclidiene LA PATRAT intre randurile lui A si B.

    Foloseste identitatea ||a - b||^2 = ||a||^2 - 2 a.b + ||b||^2 (vectorizat, fara
    bucle). Clip la 0 ca erorile de rotunjire sa nu dea valori negative mici."""
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    a2 = np.sum(A * A, axis=1).reshape(-1, 1)   # (na, 1)
    b2 = np.sum(B * B, axis=1).reshape(1, -1)   # (1, nb)
    d2 = a2 - 2.0 * (A @ B.T) + b2
    return np.maximum(d2, 0.0)


# ============================================================ k-NN
class KNN:
    """Clasificator k-NN: memoreaza setul de antrenare, voteaza pe cei k vecini.

    Etichetele pot fi orice intregi >= 0. La egalitate de voturi, alege eticheta cu
    indicele cel mai mic (numpy.bincount/argmax) -- determinist."""

    def __init__(self, k=3):
        if k < 1:
            raise ValueError("k trebuie >= 1, primit %d" % k)
        self.k = int(k)
        self.X = None
        self.y = None

    def fit(self, X, y):
        self.X = np.asarray(X, dtype=float)
        self.y = np.asarray(y).astype(int).reshape(-1)
        if self.X.shape[0] < self.k:
            raise ValueError("k=%d > numarul de exemple de antrenare %d"
                             % (self.k, self.X.shape[0]))
        return self

    def predict(self, X):
        X = np.asarray(X, dtype=float)
        d2 = pairwise_sq_dists(X, self.X)            # (m, n)
        # indicii celor k cele mai mici distante, pe fiecare rand (nesortati intre ei)
        nn = np.argpartition(d2, self.k - 1, axis=1)[:, :self.k]
        n_clase = int(self.y.max()) + 1
        out = np.empty(X.shape[0], dtype=int)
        for i in range(X.shape[0]):
            voturi = np.bincount(self.y[nn[i]], minlength=n_clase)
            out[i] = int(np.argmax(voturi))
        return out


# ============================================================ SVM LINIAR (Pegasos)
def pegasos_svm(X, y, lam=0.01, n_epoci=50, seed=0):
    """SVM liniar antrenat cu Pegasos (subgradient stocastic) pe hinge + (lam/2)||w||^2.

    Asteapta etichete y in {-1, +1}. Modelul e fara intercept explicit -- adauga o
    coloana de 1 in X daca vrei bias (vezi utils.add_bias).

    Regula de actualizare la pasul t (rata eta_t = 1/(lam*t)):
      daca y_i * <w, x_i> < 1:  w <- (1 - eta_t*lam) w + eta_t * y_i * x_i
      altfel:                   w <- (1 - eta_t*lam) w

    Returneaza vectorul de greutati w (forma (d,))."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    n, d = X.shape
    w = np.zeros(d)
    g = np.random.default_rng(seed)
    t = 0
    for _ in range(n_epoci):
        for i in g.permutation(n):
            t += 1
            eta = 1.0 / (lam * t)
            margine = y[i] * (X[i] @ w)
            if margine < 1.0:
                w = (1.0 - eta * lam) * w + eta * y[i] * X[i]
            else:
                w = (1.0 - eta * lam) * w
    return w


def svm_predict(X, w):
    """Eticheta SVM in {-1, +1} = semnul scorului <w, x>. Scor 0 -> +1 (conventie)."""
    X = np.asarray(X, dtype=float)
    scor = X @ np.asarray(w, dtype=float)
    return np.where(scor >= 0.0, 1, -1)


def hinge_loss(X, y, w, lam=0.0):
    """Pierderea hinge medie + termenul de regularizare (lam/2)||w||^2.

    L(w) = (1/n) sum_i max(0, 1 - y_i <w, x_i>) + (lam/2) ||w||^2."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    w = np.asarray(w, dtype=float)
    margini = y * (X @ w)
    hinge = np.mean(np.maximum(0.0, 1.0 - margini))
    return float(hinge + 0.5 * lam * float(w @ w))


# ============================================================ KERNEL RBF
def rbf_kernel(A, B, gamma=1.0):
    """Matrice kernel RBF K[i, j] = exp(-gamma * ||A_i - B_j||^2).

    gamma > 0 controleaza latimea: gamma mare = nucleu ingust (granita zbarlita),
    gamma mic = nucleu lat (granita neteda). Valori in (0, 1]; =1 cand A_i == B_j."""
    if gamma <= 0:
        raise ValueError("gamma trebuie > 0, primit %r" % (gamma,))
    d2 = pairwise_sq_dists(A, B)
    return np.exp(-gamma * d2)


# ============================================================ SELFTEST
def _two_clusters(n=40, seed=0):
    """Doua cluster-e gaussiene bine separate in 2D, etichete 0 si 1."""
    g = np.random.default_rng(seed)
    a = g.normal([-3.0, -3.0], 0.5, size=(n, 2))
    b = g.normal([+3.0, +3.0], 0.5, size=(n, 2))
    X = np.vstack([a, b])
    y = np.concatenate([np.zeros(n, dtype=int), np.ones(n, dtype=int)])
    return X, y


def _linsep(n=80, seed=1):
    """Date liniar separabile cu o marja clara, etichete in {-1, +1}."""
    g = np.random.default_rng(seed)
    Xp = g.normal([+2.5, +2.5], 0.6, size=(n, 2))
    Xn = g.normal([-2.5, -2.5], 0.6, size=(n, 2))
    X = np.vstack([Xp, Xn])
    y = np.concatenate([np.ones(n), -np.ones(n)])
    return X, y


def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # --- distante: caz cunoscut de mana
    A = np.array([[0.0, 0.0], [3.0, 4.0]])
    d2 = pairwise_sq_dists(A, A)
    ck("dists: ||(0,0)-(3,4)||^2 = 25", abs(d2[0, 1] - 25.0) < 1e-9)
    ck("dists: diagonala = 0", np.allclose(np.diag(d2), 0.0))

    # --- k-NN, k=1: clasifica PERFECT punctele de antrenare (vecinul = el insusi)
    Xc, yc = _two_clusters(n=40, seed=0)
    knn1 = KNN(k=1).fit(Xc, yc)
    ck("knn k=1: acuratete 100% pe propriul set de antrenare",
       accuracy(yc, knn1.predict(Xc)) == 1.0)

    # --- k-NN, k=3: cluster-e separate clasificate corect pe puncte noi
    knn3 = KNN(k=3).fit(Xc, yc)
    g = np.random.default_rng(7)
    Xtest = np.vstack([g.normal([-3.0, -3.0], 0.5, size=(20, 2)),
                       g.normal([+3.0, +3.0], 0.5, size=(20, 2))])
    ytest = np.concatenate([np.zeros(20, dtype=int), np.ones(20, dtype=int)])
    ck("knn k=3: acuratete > 0.95 pe doua cluster-e separate",
       accuracy(ytest, knn3.predict(Xtest)) > 0.95)

    # exemplul numeric din teorie.md: 4 puncte de antrenare, o interogare
    Xt = np.array([[0.0, 0.0], [1.0, 0.0], [4.0, 4.0], [5.0, 4.0]])
    yt = np.array([0, 0, 1, 1])
    q = np.array([[1.5, 0.5]])
    ck("knn k=1 pe exemplul din teorie -> clasa 0", KNN(k=1).fit(Xt, yt).predict(q)[0] == 0)
    ck("knn k=3 pe exemplul din teorie -> clasa 0", KNN(k=3).fit(Xt, yt).predict(q)[0] == 0)

    # --- Pegasos: separa date liniar separabile
    Xl, yl = _linsep(n=80, seed=1)
    w = pegasos_svm(Xl, yl, lam=0.01, n_epoci=50, seed=0)
    acc = accuracy(yl, svm_predict(Xl, w))
    ck("pegasos: acuratete > 0.95 pe date liniar separabile", acc > 0.95)
    ck("pegasos: pierderea hinge mica dupa antrenare (< 0.3)",
       hinge_loss(Xl, yl, w, lam=0.01) < 0.3)
    ck("pegasos: determinist la aceeasi samanta",
       np.allclose(w, pegasos_svm(Xl, yl, lam=0.01, n_epoci=50, seed=0)))

    # --- kernel RBF: simetric, =1 pe diagonala, in (0, 1] in afara
    Xk = np.random.default_rng(3).normal(size=(6, 4))
    K = rbf_kernel(Xk, Xk, gamma=0.5)
    ck("rbf: simetric", np.allclose(K, K.T))
    ck("rbf: =1 pe diagonala", np.allclose(np.diag(K), 1.0))
    off = K[~np.eye(6, dtype=bool)]
    ck("rbf: valori in afara diagonalei in (0, 1)", np.all(off > 0.0) and np.all(off < 1.0))
    ck("rbf: gamma mare scade similaritatea fata de gamma mic",
       rbf_kernel(np.array([[0.0]]), np.array([[1.0]]), gamma=5.0)[0, 0]
       < rbf_kernel(np.array([[0.0]]), np.array([[1.0]]), gamma=0.1)[0, 0])

    print("\nTOATE VERIFICARILE knn_svm_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
