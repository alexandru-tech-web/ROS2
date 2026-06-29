#!/usr/bin/env python3
"""date_features_core.py -- feature engineering PUR in numpy (M04).

Implementeaza de la zero, fara scikit-learn, transformarile uzuale de pregatire
a datelor inainte de un model:

  1. one-hot encoding   -- categorie nominala -> vector indicator (o singura
     pozitie 1 per rand). Pentru K categorii folosim K coloane (sau K-1 daca
     drop_first=True, ca sa evitam coliniaritatea cu interceptul).
  2. encodare ordinala  -- categorie cu ordine naturala -> intreg, dupa o
     ordine data explicit (de ex. 'mic' < 'mediu' < 'mare').
  3. imputare cu media  -- valorile lipsa (NaN) inlocuite cu media coloanei.
     CRUCIAL: media se invata pe TRAIN si se aplica pe TEST (fara scurgere).
  4. feature-uri polinomiale -- ridicarea unui set de coloane la combinatii de
     grad <= d (inclusiv interactiuni si, optional, biasul). Numarul de coloane
     pentru d=2 fara bias pe p intrari este p (liniar) + p (patrate) +
     C(p,2) (interactiuni) = 2p + p(p-1)/2.
  5. detectie outlieri (IQR) -- regula Tukey: un punct e outlier daca e in afara
     intervalului [Q1 - k*IQR, Q3 + k*IQR], cu IQR = Q3 - Q1 si k=1.5 implicit.

Notatie:
  - X : matrice (n, p) de feature-uri numerice.
  - mean_tr : vectorul mediilor pe coloane, calculat IGNORAND NaN pe TRAIN.
  - quartile Q1, Q3 : percentilele 25 si 75 (interpolare liniara).

Toate functiile sunt deterministe (nu folosesc aleator). Selftest-ul de la final
verifica fiecare proprietate pe un caz mic, cunoscut de mana.

ONESTITATE: modulul nu produce date; cand e folosit (demo_sil.py) datele provin
din date_sar, care sunt SINTETICE, semanate din campaniile reale C1/M.

Ruleaza: python3 date_features_core.py   (iesire 0 = PASS, non-0 = FAIL).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml


# ============================================================ one-hot encoding
def fit_one_hot(values):
    """Invata vocabularul de categorii (sortat) dintr-un vector de etichete.

    Returneaza lista de categorii unice, in ordine stabila (sortata). Aceasta e
    'starea' encoderului: pe TEST refolosim ACEEASI ordine ca pe TRAIN.
    """
    cats = sorted(set(str(v) for v in np.asarray(values).ravel()))
    return cats


def transform_one_hot(values, categories, drop_first=False):
    """Transforma etichete in matrice indicator (n, K) folosind `categories`.

    Fiecare rand are exact un 1 (in coloana categoriei sale) si rest 0. Categorii
    nevazute la fit -> rand integral 0 (semnal explicit de 'necunoscut'). Daca
    drop_first=True se omite prima categorie (K-1 coloane), util ca sa eviti
    coliniaritatea perfecta cu coloana de bias.
    """
    values = [str(v) for v in np.asarray(values).ravel()]
    index = {c: j for j, c in enumerate(categories)}
    K = len(categories)
    M = np.zeros((len(values), K), dtype=float)
    for i, v in enumerate(values):
        j = index.get(v, None)
        if j is not None:
            M[i, j] = 1.0
    if drop_first:
        M = M[:, 1:]
    return M


def one_hot_feature_names(categories, prefix="cat", drop_first=False):
    """Numele coloanelor produse de transform_one_hot (pentru lizibilitate)."""
    cols = ["%s=%s" % (prefix, c) for c in categories]
    if drop_first:
        cols = cols[1:]
    return cols


# ============================================================ encodare ordinala
def fit_ordinal(order):
    """Construieste maparea categorie -> rang intreg din ordinea DATA explicit.

    `order` e o lista de la cea mai mica la cea mai mare categorie. Ordinea NU se
    deduce din date (ar fi arbitrara): o impune cunoasterea domeniului.
    """
    return {str(c): i for i, c in enumerate(order)}


def transform_ordinal(values, mapping, unknown=-1):
    """Mapeaza etichete pe ranguri intregi conform `mapping`; necunoscute->unknown."""
    values = [str(v) for v in np.asarray(values).ravel()]
    return np.array([mapping.get(v, unknown) for v in values], dtype=float)


# ============================================================ imputare cu media
def fit_mean_imputer(X_train):
    """Invata media pe coloane IGNORAND NaN, pe TRAIN. Returneaza vector (p,).

    O coloana integral NaN primeste media 0.0 (nu avem informatie -- alegere
    explicita, semnalata)."""
    X = np.asarray(X_train, dtype=float)
    means = np.nanmean(np.where(np.isnan(X), np.nan, X), axis=0)
    means = np.where(np.isnan(means), 0.0, means)
    return means


def transform_mean_imputer(X, means):
    """Inlocuieste fiecare NaN cu media coloanei sale (invatata pe TRAIN)."""
    X = np.asarray(X, dtype=float).copy()
    idx = np.where(np.isnan(X))
    X[idx] = np.take(means, idx[1])
    return X


# ============================================================ polinomiale
def polynomial_features(X, degree=2, include_bias=False):
    """Genereaza feature-uri polinomiale pana la `degree` (interactiuni incluse).

    Pentru p coloane de intrare, ordinea coloanelor de iesire este:
      [bias?] [grad 1: x1..xp] [grad 2: x1^2, x1*x2, ..., xp^2] [grad 3 ...] ...
    adica, pentru fiecare grad d de la 1 la `degree`, toate combinatiile cu
    repetitie de marime d ale indicilor coloanelor (multi-indici nedescrescatori).

    Numar de coloane (fara bias) = sum_{d=1}^{degree} C(p + d - 1, d).
    Pentru p, degree=2 da: p + p(p+1)/2  (liniar + patrate + interactiuni).
    """
    from itertools import combinations_with_replacement

    X = np.asarray(X, dtype=float)
    n, p = X.shape
    cols = []
    names = []
    if include_bias:
        cols.append(np.ones(n))
        names.append("1")
    for d in range(1, degree + 1):
        for combo in combinations_with_replacement(range(p), d):
            col = np.ones(n)
            for j in combo:
                col = col * X[:, j]
            cols.append(col)
            names.append("*".join("x%d" % (j + 1) for j in combo))
    return np.column_stack(cols), names


def n_polynomial_features(p, degree=2, include_bias=False):
    """Numarul de coloane pe care le-ar produce polynomial_features (formula)."""
    from math import comb

    total = 1 if include_bias else 0
    for d in range(1, degree + 1):
        total += comb(p + d - 1, d)
    return total


# ============================================================ outlieri (IQR)
def iqr_bounds(x, k=1.5):
    """Pragurile Tukey (lo, hi) pe un vector 1D: Q1-k*IQR, Q3+k*IQR."""
    x = np.asarray(x, dtype=float).ravel()
    q1, q3 = np.percentile(x, 25), np.percentile(x, 75)
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def iqr_outlier_mask(x, k=1.5):
    """Masca booleana True acolo unde valoarea e outlier dupa regula IQR."""
    x = np.asarray(x, dtype=float).ravel()
    lo, hi = iqr_bounds(x, k=k)
    return (x < lo) | (x > hi)


# ============================================================ selftest
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # ---- one-hot: o singura pozitie 1 per rand, ordine stabila ----
    labels = ["DDS", "Zenoh", "DDS", "Zenoh", "Zenoh"]
    cats = fit_one_hot(labels)
    ck("one-hot: vocabular sortat = ['DDS','Zenoh']", cats == ["DDS", "Zenoh"])
    M = transform_one_hot(labels, cats)
    ck("one-hot: forma (5, 2)", M.shape == (5, 2))
    ck("one-hot: exact un 1 pe fiecare rand", np.array_equal(M.sum(axis=1), np.ones(5)))
    ck("one-hot: valori doar 0/1", set(np.unique(M).tolist()).issubset({0.0, 1.0}))
    # randul 0 e 'DDS' -> coloana 0 aprinsa; randul 1 'Zenoh' -> coloana 1
    ck("one-hot: codare corecta rand 0 (DDS)", M[0, 0] == 1.0 and M[0, 1] == 0.0)
    ck("one-hot: codare corecta rand 1 (Zenoh)", M[1, 0] == 0.0 and M[1, 1] == 1.0)
    # categorie nevazuta -> rand integral 0
    Mu = transform_one_hot(["DDS", "ALTCEVA"], cats)
    ck("one-hot: categorie necunoscuta -> rand 0", Mu[1].sum() == 0.0)
    # drop_first scade o coloana
    Md = transform_one_hot(labels, cats, drop_first=True)
    ck("one-hot: drop_first -> K-1 coloane", Md.shape == (5, 1))

    # ---- ordinal: respecta ordinea domeniului ----
    order = ["mic", "mediu", "mare"]
    mp = fit_ordinal(order)
    enc = transform_ordinal(["mare", "mic", "mediu", "mic"], mp)
    ck("ordinal: maparea respecta ordinea data", np.array_equal(enc, [2, 0, 1, 0]))
    ck("ordinal: mic < mediu < mare", mp["mic"] < mp["mediu"] < mp["mare"])
    enc_u = transform_ordinal(["xxl"], mp, unknown=-1)
    ck("ordinal: necunoscut -> -1", enc_u[0] == -1)

    # ---- imputare cu media de pe TRAIN (fara scurgere) ----
    # train: coloana 0 = [1,2,3,nan,4] -> media (ignorand NaN) = 2.5
    Xtr = np.array([[1.0, 10.0],
                    [2.0, 20.0],
                    [3.0, np.nan],
                    [np.nan, 40.0],
                    [4.0, 50.0]])
    means = fit_mean_imputer(Xtr)
    ck("imputare: media col 0 = 2.5 (ignora NaN)", abs(means[0] - 2.5) < 1e-12)
    ck("imputare: media col 1 = 30.0 (ignora NaN)", abs(means[1] - 30.0) < 1e-12)
    Xtr_i = transform_mean_imputer(Xtr, means)
    ck("imputare: niciun NaN dupa transform", not np.isnan(Xtr_i).any())
    ck("imputare: NaN train inlocuit cu media train", abs(Xtr_i[3, 0] - 2.5) < 1e-12)
    # TEST: un NaN nou trebuie umplut cu media de pe TRAIN, NU recalculata pe test
    Xte = np.array([[np.nan, 999.0],
                    [7.0, np.nan]])
    Xte_i = transform_mean_imputer(Xte, means)
    ck("imputare: NaN test foloseste media TRAIN (col 0 = 2.5)", abs(Xte_i[0, 0] - 2.5) < 1e-12)
    ck("imputare: NaN test foloseste media TRAIN (col 1 = 30.0)", abs(Xte_i[1, 1] - 30.0) < 1e-12)
    # demonstram explicit ABSENTA scurgerii: media test e alta decat media train
    mean_test_col0 = np.nanmean(Xte[:, 0])  # = 7.0
    ck("imputare: nu foloseste media de pe TEST (7.0 != 2.5)", abs(mean_test_col0 - 2.5) > 1.0)

    # ---- polinomiale grad 2: numar corect de coloane ----
    Xp = np.array([[2.0, 3.0],
                   [1.0, 5.0]])
    P, names = polynomial_features(Xp, degree=2, include_bias=False)
    # p=2, degree=2, fara bias -> 2 + 3 = 5 coloane: x1, x2, x1^2, x1*x2, x2^2
    ck("poly: numar coloane d=2,p=2,bias=0 -> 5", P.shape[1] == 5)
    ck("poly: numar coloane = formula", P.shape[1] == n_polynomial_features(2, 2, False))
    ck("poly: nume coloane corecte",
       names == ["x1", "x2", "x1*x1", "x1*x2", "x2*x2"])
    # rand 0 = [2,3]: x1=2, x2=3, x1^2=4, x1*x2=6, x2^2=9
    ck("poly: valori rand 0 corecte", np.array_equal(P[0], [2.0, 3.0, 4.0, 6.0, 9.0]))
    Pb, _ = polynomial_features(Xp, degree=2, include_bias=True)
    ck("poly: include_bias adauga o coloana de 1", Pb.shape[1] == 6 and np.array_equal(Pb[:, 0], [1, 1]))
    # verificare formula pentru un caz mai mare: p=3, d=3 -> 1+3 + 6 + 10 = 19 (fara bias)
    ck("poly: formula p=3,d=3,bias=0 -> 19", n_polynomial_features(3, 3, False) == 3 + 6 + 10)

    # ---- IQR: marcheaza outlierii cunoscuti ----
    # masa de date 'normale' 1..11 + un outlier sus (100) si unul jos (-50)
    base = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], dtype=float)
    x = np.concatenate([base, [100.0, -50.0]])
    mask = iqr_outlier_mask(x, k=1.5)
    ck("iqr: marcheaza outlierul mare (100)", mask[11] == True)
    ck("iqr: marcheaza outlierul mic (-50)", mask[12] == True)
    ck("iqr: nu marcheaza punctele normale", not mask[:11].any())
    lo, hi = iqr_bounds(base, k=1.5)
    # base 1..11: Q1=3.5? percentila 25 cu interpolare -> 3.5; Q3=8.5; IQR=5; lo=-4; hi=16
    ck("iqr: pragurile pe 1..11 sunt [-4, 16]", abs(lo - (-4.0)) < 1e-9 and abs(hi - 16.0) < 1e-9)

    print("\nTOATE VERIFICARILE date_features_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
