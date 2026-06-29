#!/usr/bin/env python3
"""evaluare_validare_core.py -- nucleul M07, numpy pur (scikit-learn INTERZIS).

Evaluare onesta a unui model: impartire in falduri (k-fold), LOOCV (critic la N
mic), validare incrucisata generica si curbe de invatare. Metricele (RMSE/MAE/R2)
vin din utils (SURSA UNICA).

API generic: functiile primesc un callback `fit_predict(X_tr, y_tr, X_te) -> y_pred`
ca sa fie independente de model (regresie liniara, ridge, etc.).

Determinism: amestecarea faldurilor trece prin numpy.random.default_rng(seed).
_selftest() verifica:
  - k-fold acopera TOTI indicii fara suprapunere, in k falduri ~egale;
  - LOOCV produce n falduri de marime 1;
  - cross_val pe date liniare cu model liniar da RMSE mic;
  - curba de invatare: eroarea de validare scade cand creste setul de antrenare.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python evaluare_validare_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import rmse, add_bias  # noqa: E402


# ============================================================ FALDURI
def kfold_indices(n, k, seed=0, shuffle=True):
    """Imparte indicii 0..n-1 in k falduri ~egale. Returneaza o lista de
    (train_idx, test_idx) ca array-uri numpy. Cu shuffle, ordinea e amestecata
    determinist prin seed."""
    if not 2 <= k <= n:
        raise ValueError("k trebuie in [2, n], primit k=%d, n=%d" % (k, n))
    idx = np.arange(n)
    if shuffle:
        idx = np.random.default_rng(seed).permutation(n)
    folds = np.array_split(idx, k)
    out = []
    for i in range(k):
        test = folds[i]
        train = np.concatenate([folds[j] for j in range(k) if j != i])
        out.append((np.sort(train), np.sort(test)))
    return out


def loocv_indices(n):
    """Leave-one-out: n falduri, fiecare cu un singur index de test."""
    return kfold_indices(n, k=n, shuffle=False)


# ============================================================ CROSS-VALIDATION
def cross_val_score(X, y, fit_predict, k=5, metric=rmse, seed=0):
    """Scor de validare incrucisata per fald. fit_predict(X_tr,y_tr,X_te)->y_pred.
    Returneaza un array de scoruri (unul per fald)."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    scores = []
    for tr, te in kfold_indices(X.shape[0], k, seed=seed):
        y_pred = fit_predict(X[tr], y[tr], X[te])
        scores.append(metric(y[te], y_pred))
    return np.array(scores)


def cv_summary(scores):
    """Rezumat al scorurilor CV: media si abaterea (esantion)."""
    scores = np.asarray(scores, dtype=float)
    return dict(mean=float(scores.mean()),
                std=float(scores.std(ddof=1)) if scores.size > 1 else 0.0,
                n=int(scores.size))


# ============================================================ CURBA DE INVATARE
def learning_curve(X, y, fit_predict, train_sizes, metric=rmse, seed=0):
    """Eroare de TRAIN si de VALIDARE vs marimea setului de antrenare.

    Tine deoparte 25% pentru validare (fix, seed), apoi antreneaza pe prefixe de
    marime crescatoare din restul. Returneaza (train_err, val_err) ca array-uri
    aliniate cu train_sizes."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    n = X.shape[0]
    perm = np.random.default_rng(seed).permutation(n)
    n_val = max(1, int(round(0.25 * n)))
    val, pool = perm[:n_val], perm[n_val:]
    tr_err, va_err = [], []
    for m in train_sizes:
        m = min(m, pool.size)
        sub = pool[:m]
        y_tr_pred = fit_predict(X[sub], y[sub], X[sub])
        y_va_pred = fit_predict(X[sub], y[sub], X[val])
        tr_err.append(metric(y[sub], y_tr_pred))
        va_err.append(metric(y[val], y_va_pred))
    return np.array(tr_err), np.array(va_err)


# ============================================================ SELFTEST
def _ols_fit_predict(X_tr, y_tr, X_te):
    """Model auxiliar pentru teste: regresie liniara cu bias (ecuatii normale)."""
    Phi = add_bias(X_tr)
    w, *_ = np.linalg.lstsq(Phi, y_tr, rcond=None)
    return add_bias(X_te) @ w


def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # k-fold: acoperire completa, fara suprapunere
    folds = kfold_indices(20, k=5, seed=0)
    ck("kfold: 5 falduri", len(folds) == 5)
    all_test = np.concatenate([te for _, te in folds])
    ck("kfold: testele acopera toti indicii o data",
       sorted(all_test.tolist()) == list(range(20)))
    for tr, te in folds:
        ck_overlap = len(set(tr.tolist()) & set(te.tolist())) == 0
        assert ck_overlap, "FAIL: kfold suprapunere train/test"
    ok += 1
    print("  [ok] kfold: train si test disjuncte in fiecare fald")
    ck("kfold: fiecare fald de test are 4 elemente", all(len(te) == 4 for _, te in folds))

    # LOOCV
    loo = loocv_indices(12)
    ck("loocv: 12 falduri de marime 1", len(loo) == 12 and all(len(te) == 1 for _, te in loo))

    # cross_val pe date liniare: RMSE mic
    rng = np.random.default_rng(1)
    X = rng.uniform(-2, 2, size=(120, 3))
    w_true = np.array([1.5, -2.0, 0.7])
    y = X @ w_true + 1.0 + 0.05 * rng.standard_normal(120)
    sc = cross_val_score(X, y, _ols_fit_predict, k=5, seed=0)
    summ = cv_summary(sc)
    ck("cross_val: 5 scoruri", summ["n"] == 5)
    ck("cross_val: RMSE mic pe date liniare (< 0.2)", summ["mean"] < 0.2)

    # curba de invatare: validarea se imbunatateste cu mai multe date
    # tinta neliniara, model liniar -> eroarea scade apoi se aseaza
    Xn = rng.uniform(-2, 2, size=(200, 1))
    yn = np.sin(Xn[:, 0]) + 0.1 * rng.standard_normal(200)
    tr_err, va_err = learning_curve(Xn, yn, _ols_fit_predict,
                                    train_sizes=[5, 15, 40, 100], seed=2)
    ck("learning_curve: eroarea de validare la set mare <= la set mic",
       va_err[-1] <= va_err[0] + 1e-9)

    print("\nTOATE VERIFICARILE evaluare_validare_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
