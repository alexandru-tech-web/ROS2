#!/usr/bin/env python3
"""solutii.py -- solutiile complete pentru exercitii.py (M00).

Rulat cu venv-ul cursului TREBUIE sa TREACA (exit 0). Fisier separat de stub-uri
ca cititorul sa incerce intai singur.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python solutii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from algebra_liniara_core import covariance, norm, power_iteration  # noqa: E402
from date_sar import make_latency_dataset                          # noqa: E402

FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m", "rtt_ms"]


# ---------------------------------------------------------------- Exercitiul 1
def cosine_similarity(x, y):
    """cos(x, y) = <x, y> / (||x||_2 ||y||_2); 0.0 daca un vector e ~0."""
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    nx = norm(x, 2)
    ny = norm(y, 2)
    if nx < 1e-300 or ny < 1e-300:
        return 0.0
    return float(np.sum(x * y) / (nx * ny))


# ---------------------------------------------------------------- Exercitiul 2
def project_onto_basis(x, Q):
    """p = Q (Q^T x) pentru Q ortonormal; reziduu = x - p (ortogonal pe coloane)."""
    x = np.asarray(x, dtype=float).ravel()
    Q = np.asarray(Q, dtype=float)
    coeffs = Q.T @ x                       # coordonatele in baza ortonormala
    p = Q @ coeffs
    r = x - p
    return p, r


# ---------------------------------------------------------------- Exercitiul 3
def explained_variance_ratio(C):
    """(lambda_i / sum lambda) sortat descrescator, din numpy.linalg.eigh."""
    C = np.asarray(C, dtype=float)
    w = np.linalg.eigvalsh(C)              # crescator, real (C simetrica)
    w = np.clip(w, 0.0, None)              # numeric: zero-uri usor negative -> 0
    w = np.sort(w)[::-1]                   # descrescator
    total = float(np.sum(w))
    if total < 1e-300:
        return np.zeros_like(w)
    return w / total


# ---------------------------------------------------------------- Exercitiul 4
def dominant_axis_latency(seed=0):
    """Axa dominanta a covariantei feature-urilor standardizate de telemetrie."""
    df = make_latency_dataset(n_per_cond=200, seed=seed)
    X = df[FEATURES].to_numpy(dtype=float)
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std_safe = np.where(std < 1e-12, 1.0, std)
    Xs = (X - mean) / std_safe
    C = covariance(Xs)
    lam, v = power_iteration(C, num_iter=5000, seed=1)
    v = v / norm(v, 2)
    return lam, v


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # E1
    ck("E1: cos(x, x) = 1", abs(cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) - 1.0) < 1e-9)
    ck("E1: cos vectori ortogonali = 0", abs(cosine_similarity([1.0, 0.0], [0.0, 5.0])) < 1e-9)
    ck("E1: cos antiparalel = -1", abs(cosine_similarity([1.0, 1.0], [-2.0, -2.0]) + 1.0) < 1e-9)

    # E2
    Q = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])
    x = np.array([2.0, 3.0, 7.0])
    p, r = project_onto_basis(x, Q)
    ck("E2: proiectie pe e1,e2 = (2,3,0)", np.allclose(p, [2.0, 3.0, 0.0]))
    ck("E2: reziduu ortogonal pe baza",
       abs(float(r @ Q[:, 0])) < 1e-9 and abs(float(r @ Q[:, 1])) < 1e-9)

    # E3
    C = np.diag([4.0, 1.0, 0.0])
    evr = explained_variance_ratio(C)
    ck("E3: ratii sortate descrescator si suma 1",
       np.allclose(evr, [0.8, 0.2, 0.0]) and abs(float(np.sum(evr)) - 1.0) < 1e-9)

    # E4
    lam, v = dominant_axis_latency(seed=0)
    ck("E4: vector propriu normat", abs(norm(v, 2) - 1.0) < 1e-6)
    ck("E4: valoarea proprie pozitiva si rezonabila (>1)", lam > 1.0)

    print("\nTOATE SOLUTIILE M00 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
