#!/usr/bin/env python3
"""selectie_model_sklearn.py -- validare incrucisata a nucleului M18 cu scikit-learn.

Verifica, pe ACELASI grid de grade de polinom si pe EXACT ACELEASI falduri:
  - grid_search_cv al nucleului alege ACELASI hiperparametru (gradul) ca
    sklearn.model_selection.GridSearchCV cu un pipeline polinom + regresie liniara;
  - scorurile CV per grad coincid (potrivire stransa, pentru ca faldurile sunt
    identice: dam lui sklearn chiar partitia produsa de kfold_idx al nucleului);
  - ambele aleg gradul adevarat al cubicii zgomotoase.

Dam lui sklearn aceiasi indici de fald (cv = lista de (train, test)) ca sa
eliminam diferenta de amestecare -- altfel, pe date unde gradele mari sunt aproape
la egalitate, alegerea poate bascula intre partitii diferite.

try/except ImportError -> exit 0 (sklearn lipsa nu e o eroare).
Iesire 0 daca potrivirile trec.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selectie_model_core import grid_search_cv, kfold_idx  # noqa: E402

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import PolynomialFeatures
    from sklearn.model_selection import GridSearchCV
except ImportError:
    print("[sklearn] indisponibil -- sar validarea incrucisata (nu e o eroare).")
    sys.exit(0)


def _fp_deg(X_tr, y_tr, X_te, deg):
    """Adaptor fit_predict pentru nucleu: polinom de grad `deg` din x = X[:, 0]."""
    x_tr = np.asarray(X_tr, dtype=float)[:, 0]
    x_te = np.asarray(X_te, dtype=float)[:, 0]
    Phi = np.vander(x_tr, deg + 1, increasing=True)
    w, *_ = np.linalg.lstsq(Phi, y_tr, rcond=None)
    return np.vander(x_te, deg + 1, increasing=True) @ w


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # date: cubica zgomotoasa (optim cunoscut ~ grad 3)
    g = np.random.default_rng(0)
    x = g.uniform(-2, 2, size=120)
    y = 0.5 * x ** 3 - x + 1.0 + 0.3 * g.standard_normal(120)
    X = x.reshape(-1, 1)
    grid = [1, 2, 3, 4, 5, 6]
    k, seed = 5, 0

    # --- nucleu
    best_core, sc_core, scores_core = grid_search_cv(X, y, _fp_deg, grid, k=k, seed=seed)

    # --- sklearn: pipeline PolynomialFeatures + LinearRegression, EXACT aceleasi falduri
    folds = [(tr, te) for tr, te in kfold_idx(X.shape[0], k, seed=seed)]
    pipe = make_pipeline(PolynomialFeatures(degree=1, include_bias=True),
                         LinearRegression(fit_intercept=False))
    gs = GridSearchCV(pipe,
                      param_grid={"polynomialfeatures__degree": grid},
                      scoring="neg_root_mean_squared_error", cv=folds)
    gs.fit(X, y)
    best_sk = int(gs.best_params_["polynomialfeatures__degree"])
    sc_sk = float(-gs.best_score_)  # neg_rmse -> rmse pozitiv

    ck("grid_search nucleu si sklearn aleg acelasi grad (%d)" % best_core,
       best_core == best_sk)
    ck("ambele aleg gradul adevarat 3", best_core == 3 and best_sk == 3)
    ck("scorul CV al castigatorului ~ sklearn (|d| < 1e-6, falduri identice)",
       abs(sc_core - sc_sk) < 1e-6)
    # scorurile per grad coincid (faldurile sunt identice)
    sk_per_deg = {d: float(-m) for d, m in
                  zip(grid, gs.cv_results_["mean_test_score"])}
    ck("scorurile CV per grad coincid nucleu vs sklearn",
       all(abs(scores_core[d] - sk_per_deg[d]) < 1e-6 for d in grid))

    print("\nVALIDARE INCRUCISATA M18 OK: %d potriviri." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
