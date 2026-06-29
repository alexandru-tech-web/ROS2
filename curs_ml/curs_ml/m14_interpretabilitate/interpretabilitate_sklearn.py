#!/usr/bin/env python3
"""interpretabilitate_sklearn.py -- validare incrucisata a importantei prin permutare.

Compara permutation_importance din nucleu cu sklearn.inspection.permutation_importance
pe un model sklearn simplu (regresie liniara). Verifica:
  - acelasi clasament al feature-urilor (ORDINEA importantei coincide);
  - acelasi SEMN al importantelor (feature util > 0, zgomot ~ 0);
  - feature-ul cu adevarat informativ e pe primul loc in ambele.

Toleranta laxa la valori (permutarile difera intre implementari, ca si scoring-ul);
ce verificam strict este ORDINEA si SEMNUL.

Iesire 0 daca potrivirile trec sau daca sklearn lipseste.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from interpretabilitate_core import permutation_importance  # noqa: E402
from utils import r2_score  # noqa: E402

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.inspection import permutation_importance as sk_perm
except ImportError:
    print("[sklearn] indisponibil -- sar validarea importantei prin permutare (nu e o eroare).")
    sys.exit(0)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # date: 3 feature-uri cu importanta clar ordonata, al 4-lea pur zgomot
    rng = np.random.default_rng(0)
    n = 600
    X = rng.uniform(-2, 2, size=(n, 4))
    # coeficienti descrescatori: feature 0 cel mai important, feature 3 = zgomot
    w_true = np.array([3.0, 1.5, 0.6, 0.0])
    y = X @ w_true + 0.5 + 0.05 * rng.standard_normal(n)

    model = LinearRegression().fit(X, y)
    pred = lambda Xq: model.predict(Xq)

    imp_core = permutation_importance(pred, X, y, metric=r2_score, n_repeats=20, seed=1)
    res_sk = sk_perm(model, X, y, scoring="r2", n_repeats=20, random_state=1)
    imp_sk = res_sk.importances_mean

    order_core = list(np.argsort(imp_core)[::-1])
    order_sk = list(np.argsort(imp_sk)[::-1])
    ck("clasamentul feature-urilor coincide nucleu vs sklearn", order_core == order_sk)
    ck("ambele pun feature 0 pe primul loc", order_core[0] == 0 and order_sk[0] == 0)
    ck("ambele pun feature de zgomot (3) pe ultimul loc",
       order_core[-1] == 3 and order_sk[-1] == 3)

    # semnul: feature-urile utile au importanta pozitiva, zgomotul ~0
    ck("semn: importanta feature 0 > 0 in ambele", imp_core[0] > 0 and imp_sk[0] > 0)
    ck("semn: importanta zgomotului ~0 in ambele (< 0.02)",
       abs(imp_core[3]) < 0.02 and abs(imp_sk[3]) < 0.02)

    print("\nVALIDARE INCRUCISATA M14 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
