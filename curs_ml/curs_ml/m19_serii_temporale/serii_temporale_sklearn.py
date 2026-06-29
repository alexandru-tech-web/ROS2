#!/usr/bin/env python3
"""serii_temporale_sklearn.py -- validare incrucisata a nucleului M19 cu scikit-learn.

Potrivirea AR(p) prin cele mai mici patrate este, matematic, o regresie liniara pe
matricea de lag-uri. Aici verificam:
  - fit_ar (nucleu numpy) == LinearRegression din sklearn pe ACELEASI lag-feature-uri
    (aceiasi coeficienti c si phi, sub toleranta);
  - prognoza un-pas a celor doua coincide (sub toleranta);
  - (optional) TimeSeriesSplit produce falduri care NU au look-ahead
    (max(train_idx) < min(test_idx) in fiecare fald), oglindind temporal_split.

Daca sklearn lipseste, iese 0 (nu e o eroare). Iesire 0 daca potrivirile trec.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from serii_temporale_core import (  # noqa: E402
    make_lag_features, fit_ar, _ar2_process,
)

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import TimeSeriesSplit
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

    # serie AR(2) de test
    x = _ar2_process(2000, phi1=0.5, phi2=-0.3, c=1.0, noise=0.2, seed=7)
    p = 2

    # 1) coeficienti: fit_ar (numpy) == LinearRegression (pe aceleasi lag-feature-uri)
    c_hat, phi_hat = fit_ar(x, p)
    X, y = make_lag_features(x, p)
    lr = LinearRegression().fit(X, y)
    ck("intercept c: nucleu ~ sklearn (|d| < 1e-8)", abs(c_hat - lr.intercept_) < 1e-8)
    ck("coeficienti phi: nucleu ~ sklearn (max|d| < 1e-8)",
       np.max(np.abs(phi_hat - lr.coef_)) < 1e-8)

    # 2) prognoza un-pas pe ultimul rand de lag-uri: coincide
    last_lags = X[-1].reshape(1, -1)
    pred_core = c_hat + float(phi_hat @ X[-1])
    pred_sk = float(lr.predict(last_lags)[0])
    ck("prognoza un-pas: nucleu ~ sklearn (|d| < 1e-8)", abs(pred_core - pred_sk) < 1e-8)

    # 3) TimeSeriesSplit: fara look-ahead in niciun fald (oglindeste temporal_split)
    tss = TimeSeriesSplit(n_splits=4)
    no_leak = True
    for tr_idx, te_idx in tss.split(np.arange(200)):
        if tr_idx.max() >= te_idx.min():
            no_leak = False
    ck("TimeSeriesSplit: max(train) < min(test) in fiecare fald (fara look-ahead)", no_leak)

    print("\nVALIDARE INCRUCISATA M19 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
