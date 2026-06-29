#!/usr/bin/env python3
"""pca_sklearn.py -- validare incrucisata a nucleului M16 cu scikit-learn.

Verifica pe ACELEASI date sintetice ca nucleul implementeaza acelasi PCA ca
sklearn.decomposition.PCA:
  - aceleasi ratii de varianta explicata (toleranta stransa -- aceeasi formula);
  - aceleasi valori singulare;
  - aceleasi componente PANA LA SEMN (SVD lasa semnul liber; comparam dupa ce
    aliniem semnele).

Iesire 0 daca potrivirile trec. Daca sklearn lipseste, iese 0 (nu e o eroare).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from pca_core import PCA, _fix_signs  # noqa: E402

try:
    from sklearn.decomposition import PCA as SkPCA
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

    g = np.random.default_rng(3)
    A = g.normal(size=(200, 6))
    X = A @ g.normal(size=(6, 6)) + g.uniform(-2, 2, size=6)

    mine = PCA().fit(X)
    sk = SkPCA().fit(X)

    # 1) ratiile de varianta explicata identice
    ck("ratii de varianta explicata ~ sklearn (|d| < 1e-9)",
       np.allclose(mine.explained_variance_ratio_, sk.explained_variance_ratio_, atol=1e-9))

    # 2) valorile singulare identice
    ck("valori singulare ~ sklearn (|d| < 1e-7)",
       np.allclose(mine.singular_values_, sk.singular_values_, atol=1e-7))

    # 3) componentele identice pana la semn (aliniem semnele ambelor la fel)
    comp_sk = _fix_signs(sk.components_)
    ck("componente ~ sklearn pana la semn (|d| < 1e-7)",
       np.allclose(mine.components_, comp_sk, atol=1e-7))

    # 4) proiectia pe 2D identica pana la semn
    Tk_mine = mine.transform(X, k=2)
    Tk_sk = SkPCA(n_components=2).fit_transform(X)
    # aliniem semnul pe coloane (componente fixate identic -> deja aliniate)
    ck("scoruri 2D ~ sklearn pana la semn (|d| < 1e-6)",
       np.allclose(np.abs(Tk_mine), np.abs(Tk_sk), atol=1e-6))

    print("\nVALIDARE INCRUCISATA M16 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
