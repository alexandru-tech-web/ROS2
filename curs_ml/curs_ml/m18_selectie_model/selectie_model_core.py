#!/usr/bin/env python3
"""selectie_model_core.py -- nucleul M18, numpy pur (scikit-learn INTERZIS).

Selectie de model si reglare de hiperparametri facute ONEST:
  - grid_search_cv: cauta cel mai bun hiperparametru (un singur axa, ex. gradul
    polinomului) minimizand eroarea de validare incrucisata;
  - nested_cv: bucla externa de EVALUARE peste o bucla interna de SELECTIE, ca sa
    estimezi nepartinitor eroarea unei proceduri care isi alege singura modelul;
  - aic / bic: criterii de informatie din log-verosimilitatea gaussiana (sau din
    RSS), care penalizeaza complexitatea -- aleg modelul mai simplu la potrivire egala.

API generic: functiile de cautare primesc un callback
  fit_predict(X_tr, y_tr, X_te, hp) -> y_pred
ca sa fie independente de model (grad polinom, lambda ridge, etc.).

NU importam din alte module mXX. Un k-fold simplu e reimplementat aici (kfold_idx),
ca nucleul sa fie auto-suficient (acelasi principiu ca in M07, reluat local).

Determinism: amestecarea faldurilor trece prin numpy.random.default_rng(seed).
_selftest() verifica:
  - grid_search alege gradul polinomului CORECT (optim cunoscut, cubica zgomotoasa);
  - nested CV NU e mai optimista decat eroarea de selectie (estimare >= CV de
    selectie pe date zgomotoase cu multe candidate -- supra-optimizarea pe validare);
  - AIC si BIC aleg modelul MAI SIMPLU la potrivire ~egala;
  - BIC penalizeaza complexitatea mai tare decat AIC la n mare.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python selectie_model_core.py
"""
import sys

import numpy as np


# ============================================================ FALDURI (local)
def kfold_idx(n, k, seed=0, shuffle=True):
    """Imparte indicii 0..n-1 in k falduri ~egale. Returneaza o lista de
    (train_idx, test_idx). Reimplementat local (M18 nu importa din alte module).
    Cu shuffle, ordinea e amestecata determinist prin seed."""
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


def _rmse(y_true, y_pred):
    """RMSE local (nucleul nu importa utils)."""
    y_true = np.asarray(y_true, dtype=float).reshape(-1)
    y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


# ============================================================ GRID SEARCH CV
def grid_search_cv(X, y, fit_predict, grid, k=5, metric=_rmse, seed=0):
    """Cauta pe o singura axa de hiperparametri valoarea cu eroarea CV minima.

    fit_predict(X_tr, y_tr, X_te, hp) -> y_pred. `grid` e iterabilul de valori
    candidate (ex. grade de polinom [1,2,3,...] sau lambda-uri ridge).

    Returneaza (best_hp, best_score, scores) unde `scores` e un dict
    {hp: scor_CV_mediu}. Mai mic = mai bun (metric e o EROARE)."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    folds = kfold_idx(X.shape[0], k, seed=seed)
    scores = {}
    best_hp, best_score = None, np.inf
    for hp in grid:
        errs = []
        for tr, te in folds:
            y_pred = fit_predict(X[tr], y[tr], X[te], hp)
            errs.append(metric(y[te], y_pred))
        sc = float(np.mean(errs))
        scores[hp] = sc
        if sc < best_score:
            best_score, best_hp = sc, hp
    return best_hp, best_score, scores


# ============================================================ NESTED CV
def nested_cv(X, y, fit_predict, grid, k_outer=5, k_inner=4, metric=_rmse, seed=0):
    """Validare incrucisata IMBRICATA: estimare nepartinitoare a erorii unei
    proceduri care isi alege singura hiperparametrul.

    Bucla EXTERNA (k_outer falduri) e doar pentru evaluare: pe fiecare fald de
    antrenare ruleaza grid_search_cv (bucla INTERNA, k_inner falduri) ca sa aleaga
    hiperparametrul, apoi potriveste cu el si masoara pe faldul extern de test --
    care NU a participat la selectie. Mediaza scorurile externe.

    De ce conteaza: eroarea de selectie (minimul peste grid intr-un SINGUR CV) e
    optimist partinita pentru ca am ales special valoarea care arata bine pe ACELE
    falduri. Bucla externa repara asta: testeaza pe date nevazute de selectie.

    Returneaza (mean_score, fold_scores, chosen_hps)."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    fold_scores, chosen = [], []
    for tr, te in kfold_idx(X.shape[0], k_outer, seed=seed):
        best_hp, _, _ = grid_search_cv(X[tr], y[tr], fit_predict, grid,
                                       k=k_inner, metric=metric, seed=seed + 1)
        y_pred = fit_predict(X[tr], y[tr], X[te], best_hp)
        fold_scores.append(metric(y[te], y_pred))
        chosen.append(best_hp)
    return float(np.mean(fold_scores)), np.array(fold_scores), chosen


# ============================================================ AIC / BIC
def gaussian_neg2ll(rss, n):
    """-2 ln L pentru un model gaussian cu varianta estimata prin maxima
    verosimilitate (sigma^2_hat = RSS / n).

    Verosimilitatea profilata (dupa eliminarea lui sigma) da:
      -2 ln L = n * ln(2*pi) + n * ln(RSS / n) + n.
    Constanta n*ln(2*pi)+n e aceeasi pentru orice model pe acelasi n, deci se
    anuleaza cand COMPARAM doua modele; o pastram pentru valori absolute corecte."""
    rss = float(rss)
    n = int(n)
    if rss <= 0 or n <= 0:
        raise ValueError("rss si n trebuie pozitive (rss=%r, n=%r)" % (rss, n))
    return n * np.log(2.0 * np.pi) + n * np.log(rss / n) + n


def aic(neg2ll, k):
    """Criteriul de informatie Akaike: AIC = 2k - 2 ln L = 2k + (-2 ln L).
    k = numarul de parametri liberi. Mai mic = mai bun (compromis fit/complexitate)."""
    return 2.0 * k + float(neg2ll)


def bic(neg2ll, k, n):
    """Criteriul bayesian de informatie: BIC = k ln n - 2 ln L = k*ln(n) + (-2 ln L).
    Penalizeaza complexitatea cu ln(n) per parametru: la n > e^2 ~ 7.39 penalizarea
    per parametru (ln n) depaseste pe cea a AIC (2), deci BIC prefera modele mai simple."""
    return float(k) * np.log(n) + float(neg2ll)


def aic_from_rss(rss, n, k):
    """AIC direct din RSS pentru un model gaussian (comoditate)."""
    return aic(gaussian_neg2ll(rss, n), k)


def bic_from_rss(rss, n, k):
    """BIC direct din RSS pentru un model gaussian (comoditate)."""
    return bic(gaussian_neg2ll(rss, n), k, n)


# ============================================================ AJUTOR POLINOM (teste)
def _poly_design(x, deg):
    """Matrice de design polinomiala [1, x, x^2, ..., x^deg] (Vandermonde crescator)."""
    return np.vander(np.asarray(x, dtype=float).reshape(-1), deg + 1, increasing=True)


def _fit_predict_poly(x_tr, y_tr, x_te, deg):
    """Potriveste un polinom de grad `deg` (cele mai mici patrate) si prezice."""
    Phi = _poly_design(x_tr, deg)
    w, *_ = np.linalg.lstsq(Phi, y_tr, rcond=None)
    return _poly_design(x_te, deg) @ w


# ============================================================ SELFTEST
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # ---- 1) grid_search alege gradul polinomial CORECT (optim cunoscut: cubica)
    g = np.random.default_rng(0)
    x = g.uniform(-2, 2, size=80)
    y = 0.5 * x ** 3 - x + 1.0 + 0.3 * g.standard_normal(80)
    grid = [1, 2, 3, 4, 5, 6]
    best, best_sc, scores = grid_search_cv(x.reshape(-1, 1), y, _fp_deg, grid, k=5, seed=0)
    ck("grid_search: alege gradul 3 (gradul adevarat al cubicii)", best == 3)
    ck("grid_search: scorul gradului ales e minimul din grid",
       abs(best_sc - min(scores.values())) < 1e-12)
    ck("grid_search: subpotrivirea (grad 1) e mai proasta ca optimul",
       scores[1] > scores[3])

    # ---- 2) nested CV NU e mai optimista decat eroarea de selectie
    #         (date zgomotoase + multe candidate -> selectia pe un singur CV optimizeaza
    #          zgomotul; bucla externa demasca asta). Seed ales sa arate golul clar.
    g2 = np.random.default_rng(101)
    x2 = g2.uniform(-2, 2, size=60)
    y2 = 0.5 * x2 ** 3 - x2 + 1.0 + 0.6 * g2.standard_normal(60)
    grid2 = [1, 2, 3, 4, 5, 6, 7, 8]
    _, sel_cv, _ = grid_search_cv(x2.reshape(-1, 1), y2, _fp_deg, grid2, k=5, seed=1)
    nested_mean, _, _ = nested_cv(x2.reshape(-1, 1), y2, _fp_deg, grid2,
                                  k_outer=5, k_inner=4, seed=1)
    ck("nested_cv: estimarea onesta >= eroarea de selectie (selectia e optimista)",
       nested_mean >= sel_cv - 1e-9)
    ck("nested_cv: gol strict pozitiv pe acest caz zgomotos",
       nested_mean > sel_cv)

    # ---- 3) AIC/BIC: caz lucrat numeric (n=100). Model A simplu (k=3, RSS=52)
    #         vs Model B complex (k=6, RSS=50): potrivire ~egala -> alege A.
    n = 100
    a_aic = aic_from_rss(52.0, n, 3)
    b_aic = aic_from_rss(50.0, n, 6)
    a_bic = bic_from_rss(52.0, n, 3)
    b_bic = bic_from_rss(50.0, n, 6)
    ck("aic: valoarea modelului A ~ 224.395 (caz lucrat de mana)", abs(a_aic - 224.3951) < 1e-3)
    ck("bic: valoarea modelului A ~ 232.211 (caz lucrat de mana)", abs(a_bic - 232.2106) < 1e-3)
    ck("AIC alege modelul mai SIMPLU (A) la potrivire egala", a_aic < b_aic)
    ck("BIC alege modelul mai SIMPLU (A) la potrivire egala", a_bic < b_bic)

    # ---- 4) BIC penalizeaza complexitatea mai tare decat AIC la n mare
    #         dBIC (B - A) > dAIC (B - A) > 0, fiindca ln(n) > 2 pentru n=100.
    d_aic = b_aic - a_aic
    d_bic = b_bic - a_bic
    ck("AIC: penalizarea per parametru = 2", abs((aic(0.0, 5) - aic(0.0, 4)) - 2.0) < 1e-12)
    ck("BIC: penalizarea per parametru = ln(n) (>2 la n=100)",
       abs((bic(0.0, 5, n) - bic(0.0, 4, n)) - np.log(n)) < 1e-12)
    ck("BIC penalizeaza complexitatea mai tare decat AIC la n mare (dBIC > dAIC)",
       d_bic > d_aic > 0)

    print("\nTOATE VERIFICARILE selectie_model_core AU TRECUT: %d verificari." % ok)
    return ok


def _fp_deg(X_tr, y_tr, X_te, deg):
    """Adaptor fit_predict pentru selftest: X are o coloana (x), hp = gradul."""
    return _fit_predict_poly(X_tr[:, 0], y_tr, X_te[:, 0], deg)


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
