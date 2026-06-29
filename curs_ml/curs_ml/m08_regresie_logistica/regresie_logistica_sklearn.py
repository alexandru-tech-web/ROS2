#!/usr/bin/env python3
"""regresie_logistica_sklearn.py -- validare incrucisata a nucleului M08 cu scikit-learn.

Antreneaza nucleul (coborare pe gradient de la zero) si
sklearn.linear_model.LogisticRegression pe ACELEASI date si aserteaza ca:
  - acuratetea nucleului ~ acuratetea sklearn (diferenta sub toleranta);
  - coeficientii (intercept + greutati) sunt apropiati sub toleranta laxa.

Ca sa fie comparabili, sklearn ruleaza practic fara regularizare (C foarte mare),
fiindca nucleul nostru NU regularizeaza. Diferenta de optimizator (gradient full-
batch vs lbfgs) lasa o toleranta laxa pe coeficienti.

try/except ImportError -> iesire 0 cu mesaj (sklearn lipsa nu e o eroare).
Iesire 0 daca potrivirile trec, 1 altfel.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from regresie_logistica_core import LogisticRegressionGD  # noqa: E402
from utils import standardize, accuracy  # noqa: E402

try:
    from sklearn.linear_model import LogisticRegression
except ImportError:
    print("[sklearn] indisponibil -- sar validarea incrucisata (nu e o eroare).")
    sys.exit(0)


def _make_blobs(n=300, seed=5):
    """Doua clase gaussiene moderat suprapuse in 3D (problema nebanala dar separabila)."""
    rng = np.random.default_rng(seed)
    n0 = n // 2
    X0 = rng.normal([-1.2, -1.0, 0.5], 1.0, size=(n0, 3))
    X1 = rng.normal([1.2, 1.0, -0.5], 1.0, size=(n - n0, 3))
    X = np.vstack([X0, X1])
    y = np.concatenate([np.zeros(n0), np.ones(n - n0)]).astype(int)
    return X, y


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    X, y = _make_blobs(n=300, seed=5)
    Xs, _, _, _ = standardize(X)

    # nucleul nostru
    core = LogisticRegressionGD(lr=0.3, n_iter=5000, seed=0).fit(Xs, y)
    acc_core = accuracy(y, core.predict(Xs))

    # sklearn cvasi-fara regularizare (C mare), ca sa fie comparabil cu nucleul
    sk = LogisticRegression(C=1e6, solver="lbfgs", max_iter=10000)
    sk.fit(Xs, y)
    acc_sk = accuracy(y, sk.predict(Xs))

    ck("acuratete nucleu ~ sklearn (|d| < 0.03)", abs(acc_core - acc_sk) < 0.03)

    # coeficienti: nucleul are interceptul pe pozitia 0, restul = greutati pe feature
    w_core = core.w_
    w_sk = np.concatenate([sk.intercept_.reshape(-1), sk.coef_.reshape(-1)])
    # toleranta laxa: optimizatoare diferite, dar directia/marimea trebuie sa coincida
    diff = float(np.max(np.abs(w_core - w_sk)))
    ck("coeficienti nucleu ~ sklearn (max |d| %.3f < 0.5)" % diff, diff < 0.5)

    # corelatie aproape perfecta intre cele doua seturi de coeficienti
    corr = float(np.corrcoef(w_core, w_sk)[0, 1])
    ck("coeficienti foarte corelati (corr %.4f > 0.99)" % corr, corr > 0.99)

    print("\nVALIDARE INCRUCISATA M08 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
