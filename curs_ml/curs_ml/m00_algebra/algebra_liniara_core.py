#!/usr/bin/env python3
"""algebra_liniara_core.py -- primitive de algebra liniara, PURE numpy.

Acest nucleu implementeaza DE LA ZERO blocurile de algebra liniara folosite in tot
cursul curs_ml. Niciun apel la scikit-learn aici (interzis in core). Doar numpy.

Notatie (fixata pentru intregul curs, vezi teorie.md):
  - vectori coloana x in R^n; matrice A in R^{m x n}; A^T = transpusa.
  - produs scalar:           <x, y> = x^T y = sum_i x_i y_i
  - norma L2 (euclidiana):   ||x||_2 = sqrt(<x, x>)
  - norma L1:                ||x||_1 = sum_i |x_i|
  - norma Linf (sup):        ||x||_inf = max_i |x_i|
  - proiectia lui x pe u:    proj_u(x) = (<x, u> / <u, u>) u
  - reziduul proiectiei:     r = x - proj_u(x), cu proprietatea <r, u> = 0
  - matrice de covarianta:   C = (1/(n-1)) Xc^T Xc, unde Xc = X - media coloanelor
  - valoare/vector propriu:  A v = lambda v
  - iteratia puterii:        v_{k+1} = A v_k / ||A v_k||_2 -> vectorul propriu dominant

Functii expuse:
  norm(x, ord)            -- norme L1 / L2 / Linf coerente intre ele
  dot(x, y)               -- produs scalar
  project(x, u)           -- proiectie ortogonala a lui x pe directia u
  gram_schmidt(A)         -- baza ortonormala a coloanelor lui A (QR clasic)
  covariance(X)           -- matricea de covarianta a coloanelor lui X
  power_iteration(A, ...) -- vectorul/valoarea proprie dominanta prin iteratia puterii
  matrix_rank(A, tol)     -- rang numeric via valori singulare

_selftest() verifica CORECTITUDINEA pe cazuri cunoscute:
  - proiectia produce un reziduu ORTOGONAL pe directie (<r, u> ~ 0);
  - Gram-Schmidt da coloane ortonormale (Q^T Q ~ I) care reconstruiesc spatiul;
  - iteratia puterii recupereaza vectorul propriu dominant comparat cu
    numpy.linalg.eigh (acelasi subspatiu, valoare proprie identica sub toleranta);
  - normele sunt coerente: ||x||_inf <= ||x||_2 <= ||x||_1 si scalarea liniara.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python algebra_liniara_core.py
(iesire 0 = PASS, non-0 = FAIL).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml


# ---------------------------------------------------------------- norme si produs scalar
def dot(x, y):
    """Produs scalar <x, y> = x^T y = sum_i x_i y_i."""
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    if x.shape != y.shape:
        raise ValueError("dot: dimensiuni diferite %r vs %r" % (x.shape, y.shape))
    return float(np.sum(x * y))


def norm(x, ord=2):
    """Norma vectorului x.

    ord = 1   -> ||x||_1   = sum_i |x_i|        (suma valorilor absolute)
    ord = 2   -> ||x||_2   = sqrt(sum_i x_i^2)  (euclidiana, lungimea geometrica)
    ord = inf -> ||x||_inf = max_i |x_i|        (componenta maxima in modul)

    Implementare proprie (NU numpy.linalg.norm) ca sa fie explicit ce se calculeaza.
    """
    x = np.asarray(x, dtype=float).ravel()
    if ord == 1:
        return float(np.sum(np.abs(x)))
    if ord == 2:
        return float(np.sqrt(np.sum(x * x)))
    if ord == np.inf:
        return float(np.max(np.abs(x))) if x.size else 0.0
    raise ValueError("norm: ord acceptat in {1, 2, inf}, primit %r" % (ord,))


# ---------------------------------------------------------------- proiectie ortogonala
def project(x, u):
    """Proiectia ortogonala a lui x pe directia data de u:

        proj_u(x) = (<x, u> / <u, u>) u

    Reziduul r = x - proj_u(x) este ORTOGONAL pe u: <r, u> = 0. Geometric, proj_u(x)
    e umbra lui x cazuta perpendicular pe dreapta generata de u; r e ce ramane,
    perpendicular pe acea dreapta. Daca u ~ 0, proiectia e vectorul nul.
    """
    x = np.asarray(x, dtype=float).ravel()
    u = np.asarray(u, dtype=float).ravel()
    if x.shape != u.shape:
        raise ValueError("project: dimensiuni diferite %r vs %r" % (x.shape, u.shape))
    uu = dot(u, u)
    if uu < 1e-300:
        return np.zeros_like(x)
    return (dot(x, u) / uu) * u


# ---------------------------------------------------------------- Gram-Schmidt
def gram_schmidt(A, eps=1e-12):
    """Ortonormalizeaza coloanele matricei A (Gram-Schmidt clasic).

    Pentru coloanele a_1, ..., a_k construieste vectorii ortonormali q_1, ..., q_r
    (r = numarul de coloane liniar independente) prin scaderea proiectiilor pe
    directiile deja fixate:

        u_j = a_j - sum_{i<j} proj_{q_i}(a_j)
        q_j = u_j / ||u_j||_2        (daca ||u_j|| > eps; altfel coloana e dependenta)

    Returneaza Q in R^{m x r} cu Q^T Q = I_r. Numarul de coloane pastrate (r) este
    rangul coloanelor lui A. Coloanele cvasi-nule (dependente) sunt sarite.
    """
    A = np.asarray(A, dtype=float)
    if A.ndim != 2:
        raise ValueError("gram_schmidt: asteptat matrice 2D, primit ndim=%d" % A.ndim)
    m, n = A.shape
    qs = []
    for j in range(n):
        v = A[:, j].astype(float).copy()
        for q in qs:                       # scade proiectiile pe directiile deja fixate
            v = v - dot(v, q) * q
        nv = norm(v, 2)
        if nv > eps:                       # coloana aduce o directie noua
            qs.append(v / nv)
    if not qs:
        return np.zeros((m, 0))
    return np.column_stack(qs)


# ---------------------------------------------------------------- covarianta
def covariance(X, ddof=1):
    """Matricea de covarianta a COLOANELOR lui X (X in R^{n x d}, n esantioane).

        Xc = X - media_pe_coloane(X)
        C  = (1 / (n - ddof)) Xc^T Xc          (C in R^{d x d}, simetrica, PSD)

    C[i, j] = covarianta dintre feature-ul i si feature-ul j; C[i, i] = varianta
    feature-ului i. ddof=1 da estimatorul nedeplasat (impartit la n-1).
    """
    X = np.asarray(X, dtype=float)
    if X.ndim != 2:
        raise ValueError("covariance: asteptat matrice 2D, primit ndim=%d" % X.ndim)
    n = X.shape[0]
    if n - ddof <= 0:
        raise ValueError("covariance: prea putine esantioane (n=%d, ddof=%d)" % (n, ddof))
    Xc = X - X.mean(axis=0, keepdims=True)
    return (Xc.T @ Xc) / (n - ddof)


# ---------------------------------------------------------------- iteratia puterii
def power_iteration(A, num_iter=1000, tol=1e-12, seed=0):
    """Vectorul/valoarea proprie DOMINANTA a unei matrice simetrice A (R^{d x d}).

    Iteratia puterii: pornind dintr-un v_0 aleator, repeta

        w     = A v_k
        v_{k+1} = w / ||w||_2

    Componenta de-a lungul vectorului propriu cu |lambda| maxim creste cel mai
    repede, deci v_k converge la acel vector propriu dominant. Valoarea proprie se
    recupereaza din catul Rayleigh:

        lambda = (v^T A v) / (v^T v)

    Returneaza (lambda, v) cu ||v||_2 = 1. Semnul lui v nu e unic (v si -v sunt
    ambele vectori proprii); selftest-ul compara directii, nu semne.
    """
    A = np.asarray(A, dtype=float)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError("power_iteration: asteptat matrice patratica, primit %r" % (A.shape,))
    d = A.shape[0]
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(d)
    nv = norm(v, 2)
    v = v / (nv if nv > 0 else 1.0)
    lam_prev = 0.0
    for _ in range(num_iter):
        w = A @ v
        nw = norm(w, 2)
        if nw < 1e-300:                    # A v = 0 -> v in nucleu, lambda = 0
            return 0.0, v
        v = w / nw
        lam = float(v @ (A @ v))           # catul Rayleigh (v normat -> v^T v = 1)
        if abs(lam - lam_prev) < tol:
            break
        lam_prev = lam
    lam = float(v @ (A @ v))
    return lam, v


# ---------------------------------------------------------------- rang numeric
def matrix_rank(A, tol=None):
    """Rang numeric al lui A = numarul de valori singulare semnificativ pozitive.

    Foloseste SVD (numpy.linalg.svd doar pentru valorile singulare; descompunerea
    insasi nu o reimplementam aici -- in teorie tratam SVD ca INTUITIE). Pragul
    implicit: tol = max(m, n) * sigma_max * eps_masina.
    """
    A = np.asarray(A, dtype=float)
    if A.size == 0:
        return 0
    s = np.linalg.svd(A, compute_uv=False)
    if tol is None:
        tol = max(A.shape) * (s[0] if s.size else 0.0) * np.finfo(float).eps
    return int(np.sum(s > tol))


# ---------------------------------------------------------------- selftest
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    rng = np.random.default_rng(0)

    # ---- NORME: coerente si scalare liniara ----
    x = np.array([3.0, -4.0, 0.0, 12.0])
    ck("norma L1 = sum|x| = 19", abs(norm(x, 1) - 19.0) < 1e-12)
    ck("norma L2(3,-4) caz cunoscut = 13", abs(norm(np.array([3.0, -4.0]), 2) - 5.0) < 1e-12
       and abs(norm(np.array([0.0, 5.0, 12.0]), 2) - 13.0) < 1e-12)
    ck("norma Linf = max|x| = 12", abs(norm(x, np.inf) - 12.0) < 1e-12)
    # inegalitate standard pe R^d: ||x||_inf <= ||x||_2 <= ||x||_1
    for _ in range(20):
        z = rng.standard_normal(6)
        assert norm(z, np.inf) <= norm(z, 2) + 1e-12 <= norm(z, 1) + 1e-12
    ck("coerenta norme: ||.||_inf <= ||.||_2 <= ||.||_1", True)
    a = rng.standard_normal(5)
    ck("omogenitate: ||3x|| = 3||x|| pentru toate normele",
       all(abs(norm(3.0 * a, p) - 3.0 * norm(a, p)) < 1e-10 for p in (1, 2, np.inf)))

    # ---- PRODUS SCALAR ----
    ck("dot ortogonal = 0", abs(dot([1.0, 0.0], [0.0, 1.0])) < 1e-12)
    ck("dot(x,x) = ||x||_2^2", abs(dot(a, a) - norm(a, 2) ** 2) < 1e-10)

    # ---- PROIECTIE: reziduul e ORTOGONAL pe directie ----
    for _ in range(50):
        xv = rng.standard_normal(7)
        uv = rng.standard_normal(7)
        p = project(xv, uv)
        r = xv - p
        # reziduul perpendicular pe u
        assert abs(dot(r, uv)) < 1e-9, "reziduu neortogonal"
        # proiectia e coliniara cu u (proj = alpha * u)
        assert abs(dot(p, uv) - dot(xv, uv)) < 1e-9
        # Pitagora: ||x||^2 = ||proj||^2 + ||r||^2
        assert abs(norm(xv, 2) ** 2 - (norm(p, 2) ** 2 + norm(r, 2) ** 2)) < 1e-8
    ck("proiectie: reziduul e ortogonal pe directie (<r,u> ~ 0)", True)
    ck("proiectie: descompunere Pitagora ||x||^2 = ||p||^2 + ||r||^2", True)
    # proiectia pe o axa canonica = componenta respectiva
    pe = project([2.0, 5.0, -3.0], [0.0, 1.0, 0.0])
    ck("proiectie pe axa e2 = (0,5,0)", np.allclose(pe, [0.0, 5.0, 0.0]))

    # ---- GRAM-SCHMIDT: coloane ortonormale care reconstruiesc spatiul ----
    A = rng.standard_normal((6, 4))
    Q = gram_schmidt(A)
    ck("Gram-Schmidt: Q^T Q = I (ortonormalitate)",
       np.allclose(Q.T @ Q, np.eye(Q.shape[1]), atol=1e-9))
    ck("Gram-Schmidt: rang pastrat = 4 pe matrice plina", Q.shape[1] == 4)
    # fiecare coloana a lui A e in span(Q): proiectia pe Q reconstruieste coloana
    recon = Q @ (Q.T @ A)
    ck("Gram-Schmidt: span(Q) acopera coloanele lui A", np.allclose(recon, A, atol=1e-9))
    # matrice cu o coloana dependenta -> rang 2, nu 3
    Adep = np.column_stack([A[:, 0], A[:, 1], A[:, 0] + A[:, 1]])
    ck("Gram-Schmidt: detecteaza dependenta liniara (rang 2)", gram_schmidt(Adep).shape[1] == 2)

    # ---- ITERATIA PUTERII: recupereaza vectorul propriu dominant vs numpy.linalg.eigh ----
    B = rng.standard_normal((5, 5))
    S = B @ B.T + 0.5 * np.eye(5)          # simetrica pozitiv definita -> valori proprii reale > 0
    lam_pi, v_pi = power_iteration(S, num_iter=2000, seed=1)
    w_np, V_np = np.linalg.eigh(S)         # valori proprii crescator
    lam_ref = w_np[-1]                     # dominanta (cea mai mare)
    v_ref = V_np[:, -1]
    ck("iteratia puterii: valoarea proprie ~ numpy.linalg.eigh dominanta",
       abs(lam_pi - lam_ref) / abs(lam_ref) < 1e-6)
    # acelasi vector propriu pana la semn: |cos(unghi)| ~ 1
    cosang = abs(dot(v_pi, v_ref)) / (norm(v_pi, 2) * norm(v_ref, 2))
    ck("iteratia puterii: vectorul propriu coincide ca directie (|cos| ~ 1)",
       abs(cosang - 1.0) < 1e-6)
    # verificare directa a relatiei de vector propriu: S v ~ lambda v
    ck("iteratia puterii: S v ~ lambda v (definitia vectorului propriu)",
       norm(S @ v_pi - lam_pi * v_pi, 2) < 1e-6)
    # caz diagonal cunoscut: dominanta e axa cu valoarea proprie maxima
    D = np.diag([1.0, 7.0, 3.0])
    lam_d, v_d = power_iteration(D, seed=2)
    ck("iteratia puterii: pe diag([1,7,3]) -> lambda=7, directia e2",
       abs(lam_d - 7.0) < 1e-8 and abs(abs(v_d[1]) - 1.0) < 1e-8)

    # ---- COVARIANTA: simetrica, PSD, diagonala = variante ----
    Xd = rng.standard_normal((200, 3))
    C = covariance(Xd)
    ck("covarianta: simetrica", np.allclose(C, C.T, atol=1e-12))
    ck("covarianta: coincide cu numpy.cov(rowvar=False)",
       np.allclose(C, np.cov(Xd, rowvar=False), atol=1e-10))
    eigvals = np.linalg.eigvalsh(C)
    ck("covarianta: pozitiv semidefinita (valori proprii >= 0)", np.all(eigvals > -1e-9))

    # ---- RANG ----
    ck("rang: matrice plina 4x4 are rang 4", matrix_rank(rng.standard_normal((4, 4))) == 4)
    ck("rang: coloana dublata scade rangul", matrix_rank(np.column_stack([A[:, 0], A[:, 0]])) == 1)

    print("\nTOATE VERIFICARILE algebra_liniara_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
