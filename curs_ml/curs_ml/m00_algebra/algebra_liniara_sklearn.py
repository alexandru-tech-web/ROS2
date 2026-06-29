#!/usr/bin/env python3
"""algebra_liniara_sklearn.py -- VALIDARE INCRUCISATA a nucleului de algebra liniara.

Algebra liniara nu are un 'estimator scikit-learn' direct, dar primitivele din
nucleu se valideaza cu referinte standard recunoscute:

  - iteratia puterii (vectorul propriu dominant) vs PCA-ul din scikit-learn
    (sklearn.decomposition.PCA): prima componenta principala a unor date centrate
    ESTE vectorul propriu dominant al matricei de covarianta. Le comparam ca
    directie (|cos| ~ 1) si comparam valoarea proprie dominanta cu varianta
    explicata de PCA (explained_variance_).
  - normele L1 / L2 / Linf vs numpy.linalg.norm (referinta de incredere).
  - Gram-Schmidt (Q ortonormal) vs descompunerea QR a lui numpy: span identic.

Ruleaza si nucleul si referintele pe ACELEASI date si ASERTEAZA coincidenta sub
toleranta. Tipareste comparatia. sys.exit(0) daca tot coincide, 1 altfel.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python algebra_liniara_sklearn.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from algebra_liniara_core import (  # noqa: E402
    covariance, gram_schmidt, norm, power_iteration,
)

try:
    from sklearn.decomposition import PCA
except Exception as e:  # pragma: no cover - depinde de mediu
    print("scikit-learn indisponibil: %s" % e)
    sys.exit(1)


def main():
    ok = True
    TOL = 1e-6

    def report(name, val_core, val_ref, coincide):
        nonlocal ok
        flag = "OK " if coincide else "DIFERA"
        print("  [%s] %-52s core=%s ref=%s" % (flag, name, val_core, val_ref))
        ok = ok and coincide

    rng = np.random.default_rng(7)

    # ----------------------------------------------------------------- date sintetice
    # 3 feature-uri corelate: o directie de variatie dominanta clara
    n = 500
    base = rng.standard_normal(n)
    X = np.column_stack([
        2.0 * base + 0.10 * rng.standard_normal(n),
        -1.0 * base + 0.10 * rng.standard_normal(n),
        0.20 * rng.standard_normal(n),
    ])

    print("== Validare: vector propriu dominant (nucleu) vs PCA (scikit-learn) ==")
    C = covariance(X)                                  # covarianta din nucleu
    lam_core, v_core = power_iteration(C, num_iter=5000, seed=3)

    pca = PCA(n_components=3, svd_solver="full")
    pca.fit(X)
    v_ref = pca.components_[0]                          # prima componenta principala
    lam_ref = pca.explained_variance_[0]               # varianta pe acea axa (= valoarea proprie)

    cosang = abs(float(v_core @ v_ref)) / (norm(v_core, 2) * norm(v_ref, 2))
    report("directie dominanta |cos(core, PCA)| ~ 1", round(cosang, 9), 1.0, abs(cosang - 1.0) < TOL)
    rel = abs(lam_core - lam_ref) / abs(lam_ref)
    report("valoare proprie dominanta (varianta explicata)",
           round(lam_core, 6), round(lam_ref, 6), rel < 1e-5)

    print("\n== Validare: norme (nucleu) vs numpy.linalg.norm ==")
    for _ in range(5):
        z = rng.standard_normal(8)
        for p, npord, lbl in ((1, 1, "L1"), (2, 2, "L2"), (np.inf, np.inf, "Linf")):
            a = norm(z, p)
            b = float(np.linalg.norm(z, npord))
            report("norma %s" % lbl, round(a, 9), round(b, 9), abs(a - b) < 1e-9)

    print("\n== Validare: Gram-Schmidt (nucleu) vs QR (numpy) -- acelasi span ==")
    A = rng.standard_normal((6, 4))
    Q = gram_schmidt(A)
    Qnp, _ = np.linalg.qr(A)
    # span identic <=> proiectorii ortogonali Q Q^T coincid (semnele coloanelor difera)
    Pq = Q @ Q.T
    Pn = Qnp @ Qnp.T
    same_span = np.allclose(Pq, Pn, atol=1e-8)
    report("proiectorul ortogonal pe span(coloane) coincide", "Q Q^T", "Qnp Qnp^T", same_span)
    orthonormal = np.allclose(Q.T @ Q, np.eye(Q.shape[1]), atol=1e-9)
    report("Q^T Q = I (ortonormalitate nucleu)", "Q^T Q", "I", orthonormal)

    print()
    if ok:
        print("VALIDARE INCRUCISATA: nucleul coincide cu referintele sub toleranta. PASS")
        return 0
    print("VALIDARE INCRUCISATA: DISCREPANTA. FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
