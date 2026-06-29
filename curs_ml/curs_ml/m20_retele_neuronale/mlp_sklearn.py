#!/usr/bin/env python3
"""mlp_sklearn.py -- validare incrucisata a nucleului M20 cu scikit-learn.

Antreneaza MLP-ul nostru (mlp_core, numpy pur) si un MLPRegressor din sklearn pe
ACEEASI sarcina neliniara sintetica (y = sin) si verifica faptul ca eroarea de
antrenare a nucleului e COMPARABILA cu cea a bibliotecii (toleranta laxa: ambele
ajung sub un prag mic). Nu cerem potrivire exacta -- optimizatorul, initializarea
si scalarea difera intre implementari; cerem doar ca nucleul nostru sa fie corect
(invata la fel de bine).

ONESTITATE: datele sunt SINTETICE (functie sin generata determinist).

Daca scikit-learn lipseste, iesim cu 0 (nu e o eroare).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from mlp_core import MLP  # noqa: E402
from utils import rmse  # noqa: E402

try:
    from sklearn.neural_network import MLPRegressor
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

    # sarcina neliniara comuna: y = sin(x). Date SINTETICE.
    g = np.random.default_rng(0)
    X = g.uniform(-3.0, 3.0, size=(200, 1))
    y = np.sin(X[:, 0])

    # nucleul nostru
    mine = MLP(n_hidden=16, activation="tanh", lr=0.05, n_iter=5000, seed=1).fit(X, y)
    err_mine = rmse(y, mine.predict(X))

    # sklearn pe aceeasi sarcina
    sk = MLPRegressor(hidden_layer_sizes=(16,), activation="tanh",
                      solver="lbfgs", max_iter=2000, random_state=1)
    sk.fit(X, y)
    err_sk = rmse(y, sk.predict(X))

    print("  RMSE nucleu = %.4f ; RMSE sklearn = %.4f" % (err_mine, err_sk))
    ck("nucleul invata bine functia neliniara (RMSE < 0.1)", err_mine < 0.1)
    ck("sklearn invata bine functia neliniara (RMSE < 0.1)", err_sk < 0.1)
    ck("erorile sunt comparabile (|d| < 0.1, toleranta laxa)",
       abs(err_mine - err_sk) < 0.1)

    print("\nVALIDARE INCRUCISATA M20 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
