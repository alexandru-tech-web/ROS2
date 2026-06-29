#!/usr/bin/env python3
"""evaluare_validare_sklearn.py -- validare incrucisata a nucleului M07 cu scikit-learn.

Verifica:
  - faldurile FARA amestecare ale nucleului == KFold(shuffle=False) din sklearn
    (potrivire EXACTA a indicilor de test, fald cu fald);
  - media RMSE de validare incrucisata a nucleului ~ media data de
    sklearn.model_selection.cross_val_score pe acelasi model liniar (toleranta laxa,
    fiindca amestecarea difera intre implementari).

Iesire 0 daca potrivirile trec.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from evaluare_validare_core import kfold_indices, cross_val_score, _ols_fit_predict  # noqa: E402

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import KFold, cross_val_score as sk_cvs
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

    # 1) falduri fara amestecare == sklearn KFold(shuffle=False)
    n, k = 23, 4
    mine = [te for _, te in kfold_indices(n, k, shuffle=False)]
    skf = [te for _, te in KFold(n_splits=k, shuffle=False).split(np.arange(n))]
    same = all(np.array_equal(mine[i], np.sort(skf[i])) for i in range(k))
    ck("falduri fara amestecare == sklearn KFold(shuffle=False)", same)

    # 2) media RMSE CV ~ sklearn (toleranta laxa)
    rng = np.random.default_rng(2)
    X = rng.uniform(-2, 2, size=(150, 3))
    y = X @ np.array([1.0, -1.5, 0.5]) + 0.3 + 0.1 * rng.standard_normal(150)
    mean_core = float(cross_val_score(X, y, _ols_fit_predict, k=5, seed=0).mean())
    neg_mse = sk_cvs(LinearRegression(), X, y, cv=5, scoring="neg_mean_squared_error")
    mean_sk = float(np.sqrt(-neg_mse).mean())
    ck("media RMSE CV nucleu ~ sklearn (|d| < 0.05)", abs(mean_core - mean_sk) < 0.05)

    print("\nVALIDARE INCRUCISATA M07 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
