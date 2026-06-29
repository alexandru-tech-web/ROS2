#!/usr/bin/env python3
"""pca_core.py -- nucleul M16, numpy pur (scikit-learn INTERZIS).

Analiza Componentelor Principale (PCA) prin descompunere in valori singulare
(SVD) pe date CENTRATE. PCA gaseste directiile ortogonale care explica cea mai
mare parte din varianta datelor; proiectia pe primele k directii comprima si
permite vizualizarea (de exemplu separarea conditiilor de retea pe 2D).

Legatura SVD: daca Xc = X - media e matricea centrata (n x d) si Xc = U S V^T,
atunci componentele principale sunt RANDURILE lui V^T (coloanele lui V), iar
variantele de-a lungul lor sunt s_i^2 / (n - 1). Proiectia (scorurile) este
T = Xc V = U S. Reconstructia cu k componente: Xc_hat = T_k V_k^T.

API (stil sklearn, dar pur numpy):
  fit(X)                 -> invata media, componentele, variantele explicate;
  transform(X, k)        -> proiectie pe primele k componente (scoruri);
  inverse_transform(T)   -> reconstructie inapoi in spatiul original.

Determinism: SVD e determinist; fixam semnul fiecarei componente (cel mai mare
element in valoare absoluta sa fie pozitiv) ca rezultatul sa fie reproductibil.

_selftest() verifica:
  - componentele sunt ORTONORMALE (V^T V = I);
  - ratiile de varianta explicata insumeaza 1;
  - reconstructia cu TOATE componentele == datele originale (sub toleranta);
  - pe date sintetice cu o directie dominanta, prima componenta capteaza acea
    directie (> 80% varianta);
  - transform reduce corect la k coloane.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python pca_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml


# ============================================================ SEMN DETERMINIST
def _fix_signs(components):
    """Fixeaza semnul fiecarei componente (rand) ca elementul de modul maxim sa fie
    pozitiv. SVD lasa semnul liber; asta face rezultatul reproductibil si comparabil
    cu sklearn pana la semn."""
    comp = np.array(components, dtype=float)
    for i in range(comp.shape[0]):
        j = int(np.argmax(np.abs(comp[i])))
        if comp[i, j] < 0:
            comp[i] = -comp[i]
    return comp


# ============================================================ PCA
class PCA:
    """PCA prin SVD pe date centrate. Pastreaza media, componentele (d x d, fiecare
    RAND o componenta), variantele si ratiile de varianta explicata."""

    def __init__(self):
        self.mean_ = None              # media pe coloane (d,)
        self.components_ = None        # (n_comp x d), randuri ortonormale
        self.explained_variance_ = None        # varianta pe fiecare componenta
        self.explained_variance_ratio_ = None   # fractia din varianta totala
        self.singular_values_ = None   # valorile singulare ale lui Xc

    def fit(self, X):
        """Invata componentele din X (n x d). Centreaza, face SVD, ordoneaza
        descrescator dupa varianta. Returneaza self."""
        X = np.asarray(X, dtype=float)
        n, d = X.shape
        self.mean_ = X.mean(axis=0)
        Xc = X - self.mean_
        # SVD economic: Xc = U S Vt, Vt are randuri = componente principale
        U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
        denom = max(n - 1, 1)
        var = (S ** 2) / denom
        total = var.sum()
        self.components_ = _fix_signs(Vt)
        self.singular_values_ = S
        self.explained_variance_ = var
        self.explained_variance_ratio_ = var / total if total > 0 else np.zeros_like(var)
        return self

    def transform(self, X, k=None):
        """Proiecteaza X pe primele k componente (scoruri T = Xc V_k). Daca k e None,
        foloseste toate componentele. Returneaza un array (n x k)."""
        if self.components_ is None:
            raise RuntimeError("cheama fit() inainte de transform()")
        X = np.asarray(X, dtype=float)
        comp = self.components_ if k is None else self.components_[:k]
        return (X - self.mean_) @ comp.T

    def fit_transform(self, X, k=None):
        """Comoditate: fit apoi transform pe aceleasi date."""
        return self.fit(X).transform(X, k=k)

    def inverse_transform(self, T):
        """Reconstruieste din scoruri inapoi in spatiul original. T are (n x k);
        foloseste primele k componente. Returneaza (n x d)."""
        if self.components_ is None:
            raise RuntimeError("cheama fit() inainte de inverse_transform()")
        T = np.asarray(T, dtype=float)
        k = T.shape[1]
        return T @ self.components_[:k] + self.mean_


# ============================================================ SELFTEST
def _dominant_direction_data(n=300, seed=0):
    """Date 2D cu o directie clar dominanta: imprastiere mare pe directia (1,1)/sqrt(2),
    mica perpendicular. Prima componenta trebuie sa prinda directia dominanta."""
    g = np.random.default_rng(seed)
    t = g.normal(0.0, 5.0, size=n)        # varianta mare de-a lungul directiei
    perp = g.normal(0.0, 0.3, size=n)     # varianta mica perpendicular
    u = np.array([1.0, 1.0]) / np.sqrt(2.0)
    v = np.array([-1.0, 1.0]) / np.sqrt(2.0)
    X = np.outer(t, u) + np.outer(perp, v) + np.array([10.0, -4.0])  # media deplasata
    return X, u


def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    g = np.random.default_rng(0)
    # date 5D generice pentru verificarile structurale
    A = g.normal(size=(150, 5))
    X = A @ g.normal(size=(5, 5)) + g.uniform(-3, 3, size=5)
    p = PCA().fit(X)

    # componentele ortonormale: V^T V = I (randuri ortonormale)
    G = p.components_ @ p.components_.T
    ck("componente ortonormale (V V^T = I)", np.allclose(G, np.eye(G.shape[0]), atol=1e-9))

    # ratiile de varianta insumeaza 1
    ck("ratiile de varianta explicata insumeaza 1",
       abs(p.explained_variance_ratio_.sum() - 1.0) < 1e-9)

    # ratiile sunt descrescatoare (ordonate dupa varianta)
    r = p.explained_variance_ratio_
    ck("ratiile sunt ordonate descrescator", np.all(np.diff(r) <= 1e-12))

    # reconstructie cu TOATE componentele == datele originale
    T = p.transform(X)                      # toate componentele
    Xrec = p.inverse_transform(T)
    ck("reconstructie cu toate componentele == X", np.allclose(Xrec, X, atol=1e-8))

    # transform reduce la exact k coloane
    Tk = p.transform(X, k=2)
    ck("transform(k=2) da 2 coloane", Tk.shape == (X.shape[0], 2))

    # reconstructie cu k < d are eroare > 0 (pierde informatie), dar finita
    Xk = p.inverse_transform(Tk)
    err_k = np.linalg.norm(Xk - X)
    ck("reconstructie cu k=2 < d=5 pierde informatie (eroare > 0)", err_k > 1e-6)

    # directie dominanta: prima componenta prinde directia, > 80% varianta
    Xd, u_true = _dominant_direction_data(n=400, seed=1)
    pd_ = PCA().fit(Xd)
    ck("prima componenta capteaza > 80% din varianta",
       pd_.explained_variance_ratio_[0] > 0.80)
    cos = abs(float(pd_.components_[0] @ u_true))   # |cos| ~ 1 = aliniata
    ck("prima componenta e aliniata cu directia dominanta (|cos| > 0.99)", cos > 0.99)

    # media estimata == media empirica
    ck("media estimata == media empirica", np.allclose(pd_.mean_, Xd.mean(axis=0)))

    print("\nTOATE VERIFICARILE pca_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
