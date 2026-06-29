#!/usr/bin/env python3
"""serii_temporale_core.py -- nucleul M19, numpy pur (scikit-learn INTERZIS).

Serii temporale pentru anticiparea traiectoriei: modele autoregresive AR(p),
ferestre glisante de lag-uri, potrivire prin cele mai mici patrate, prognoza
un-pas si multi-pas, split TEMPORAL (fara look-ahead, fara amestecare) si o baza
de comparatie (persistenta = ultima valoare). Metricile (RMSE) vin din utils
(SURSA UNICA).

AR(p):  x_t = c + sum_{i=1..p} phi_i x_{t-i} + eps_t
Potrivirea AR = o regresie liniara obisnuita pe matricea de lag-uri (proiectia
cea mai mica patrate a tintei pe fereastra de p valori anterioare).

Determinism: orice aleator trece prin numpy.random.default_rng(seed).
_selftest() verifica:
  - make_lag_features produce forme corecte (n-p randuri, p coloane);
  - fit_ar recupereaza coeficientii unui proces AR(1)/AR(2) generat (sub toleranta);
  - temporal_split pastreaza ordinea (max(train_idx) < min(test_idx), fara suprapunere);
  - prognoza AR bate persistenta (RMSE mai mic) pe un proces AR.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python serii_temporale_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import rmse  # noqa: E402


# ============================================================ FEATURE-URI DIN LAG-URI
def make_lag_features(series, p):
    """Fereastra glisanta -> matrice de design din lag-uri.

    Pentru o serie x_0..x_{n-1} si ordin p, construieste, pentru fiecare t >= p,
    randul de feature-uri [x_{t-1}, x_{t-2}, ..., x_{t-p}] (cel mai recent lag pe
    coloana 0) si tinta y_t = x_t. Returneaza (X, y) cu X de forma (n-p, p) si
    y de forma (n-p,). NICIUN feature din viitor -- doar valori strict anterioare."""
    x = np.asarray(series, dtype=float).reshape(-1)
    n = x.size
    if not 1 <= p < n:
        raise ValueError("p trebuie in [1, n-1], primit p=%d, n=%d" % (p, n))
    rows = n - p
    X = np.empty((rows, p))
    for j in range(p):
        # coloana j = lag (j+1): x_{t-(j+1)} pentru t = p..n-1
        X[:, j] = x[p - 1 - j: n - 1 - j]
    y = x[p:]
    return X, y


# ============================================================ POTRIVIRE AR(p)
def fit_ar(series, p):
    """Potriveste AR(p) prin cele mai mici patrate pe matricea de lag-uri.

    Modelul: x_t = c + sum_{i=1..p} phi_i x_{t-i} + eps_t. Adauga o coloana de 1
    pentru interceptul c si rezolva sistemul cu np.linalg.lstsq. Returneaza
    (c, phi) cu phi de forma (p,), unde phi[i] inmulteste lag-ul (i+1)."""
    X, y = make_lag_features(series, p)
    Phi = np.column_stack([np.ones(X.shape[0]), X])  # [1 | lag1 | ... | lagp]
    beta, *_ = np.linalg.lstsq(Phi, y, rcond=None)
    c = float(beta[0])
    phi = beta[1:].astype(float)
    return c, phi


# ============================================================ PROGNOZA
def forecast_ar(history, c, phi, steps=1):
    """Prognoza AR un-pas / multi-pas, pornind de la istoricul `history`.

    `history` trebuie sa contina cel putin p valori (p = len(phi)); foloseste
    ultimele p. Pentru steps > 1, prognoza e RECURSIVA: valorile prezise sunt
    rebagate ca lag-uri pentru pasii urmatori. Returneaza un array de lungime
    `steps`. Convingere: phi[i] inmulteste lag-ul (i+1) (cel mai recent intai)."""
    phi = np.asarray(phi, dtype=float).reshape(-1)
    p = phi.size
    hist = list(np.asarray(history, dtype=float).reshape(-1))
    if len(hist) < p:
        raise ValueError("istoric prea scurt: am nevoie de %d valori, am %d" % (p, len(hist)))
    out = np.empty(int(steps))
    for s in range(int(steps)):
        lags = np.array(hist[-1:-p - 1:-1])  # [x_{t-1}, x_{t-2}, ..., x_{t-p}]
        pred = c + float(phi @ lags)
        out[s] = pred
        hist.append(pred)
    return out


def ar_predict_onestep(test_series, c, phi, warmup):
    """Prognoze un-pas pe `test_series`, fiecare conditionata pe valorile REALE
    anterioare (nu pe propriile predictii). `warmup` = p ultime valori din TRAIN
    care preced primul punct de test (ca sa avem lag-uri pentru x_test[0]).

    Returneaza (y_true, y_pred) aliniate, ambele de lungime len(test_series)."""
    phi = np.asarray(phi, dtype=float).reshape(-1)
    p = phi.size
    warm = list(np.asarray(warmup, dtype=float).reshape(-1))[-p:]
    if len(warm) < p:
        raise ValueError("warmup prea scurt: am nevoie de %d valori" % p)
    test = np.asarray(test_series, dtype=float).reshape(-1)
    buf = warm + list(test)   # buf[p + k] = test[k]; valorile reale preced fiecare punct
    y_pred = np.empty(test.size)
    for k in range(test.size):
        # lag-uri reale [x_{t-1}, x_{t-2}, ..., x_{t-p}] pentru tinta test[k]
        lags = np.array([buf[p + k - 1 - j] for j in range(p)])
        y_pred[k] = c + float(phi @ lags)
    return test, y_pred


# ============================================================ SPLIT TEMPORAL
def temporal_split(series, train_frac=0.7):
    """Split TEMPORAL fara amestecare: primele train_frac la train, restul la test.

    Pastreaza ordinea cronologica -- ZERO look-ahead. Returneaza
    (train, test, idx_train, idx_test), unde idx_* sunt indicii (pentru a verifica
    ca max(idx_train) < min(idx_test), fara suprapunere)."""
    x = np.asarray(series, dtype=float).reshape(-1)
    n = x.size
    if not 0.0 < train_frac < 1.0:
        raise ValueError("train_frac trebuie in (0, 1), primit %r" % (train_frac,))
    n_tr = int(round(n * train_frac))
    n_tr = max(1, min(n_tr, n - 1))
    idx = np.arange(n)
    idx_tr, idx_te = idx[:n_tr], idx[n_tr:]
    return x[idx_tr], x[idx_te], idx_tr, idx_te


# ============================================================ BAZA: PERSISTENTA
def persistence_forecast(history, test_series):
    """Baza naiva (random walk): prognoza pentru x_t este x_{t-1} (ultima valoare
    reala observata). Pentru evaluare un-pas pe test, prognoza fiecarui punct de
    test este valoarea reala anterioara. Returneaza (y_true, y_pred) aliniate."""
    test = np.asarray(test_series, dtype=float).reshape(-1)
    last = float(np.asarray(history, dtype=float).reshape(-1)[-1])
    # prognoza un-pas: x_{t-1} real pentru fiecare t; primul foloseste ultima din istoric
    prev = np.concatenate([[last], test[:-1]])
    return test, prev


# ============================================================ SELFTEST
def _ar1_process(n, phi, c=0.0, noise=0.1, seed=0):
    """Genereaza un proces AR(1): x_t = c + phi*x_{t-1} + eps."""
    g = np.random.default_rng(seed)
    x = np.empty(n)
    x[0] = c / (1.0 - phi) if abs(phi) < 1 else 0.0
    for t in range(1, n):
        x[t] = c + phi * x[t - 1] + g.normal(0, noise)
    return x


def _ar2_process(n, phi1, phi2, c=0.0, noise=0.1, seed=0):
    """Genereaza un proces AR(2): x_t = c + phi1*x_{t-1} + phi2*x_{t-2} + eps."""
    g = np.random.default_rng(seed)
    x = np.zeros(n)
    for t in range(2, n):
        x[t] = c + phi1 * x[t - 1] + phi2 * x[t - 2] + g.normal(0, noise)
    return x


def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # ---- make_lag_features: forme corecte (n-p randuri, p coloane)
    x = np.arange(10.0)
    X, y = make_lag_features(x, p=3)
    ck("lag_features: forma X = (n-p, p) = (7, 3)", X.shape == (7, 3))
    ck("lag_features: forma y = (n-p,) = (7,)", y.shape == (7,))
    # randul pentru t=3: [x2, x1, x0] = [2,1,0], tinta y=x3=3
    ck("lag_features: primul rand = [x_{t-1},x_{t-2},x_{t-3}]",
       np.array_equal(X[0], [2.0, 1.0, 0.0]) and y[0] == 3.0)
    ck("lag_features: ultimul rand corect",
       np.array_equal(X[-1], [8.0, 7.0, 6.0]) and y[-1] == 9.0)

    # ---- fit_ar recupereaza coeficientii unui AR(1) generat
    phi_true = 0.7
    c_true = 2.0
    x1 = _ar1_process(4000, phi=phi_true, c=c_true, noise=0.3, seed=1)
    c_hat, phi_hat = fit_ar(x1, p=1)
    ck("fit_ar AR(1): phi recuperat (|d| < 0.05)", abs(phi_hat[0] - phi_true) < 0.05)
    ck("fit_ar AR(1): c recuperat (|d| < 0.2)", abs(c_hat - c_true) < 0.2)

    # ---- fit_ar recupereaza coeficientii unui AR(2) generat
    p1, p2 = 0.5, -0.3
    x2 = _ar2_process(6000, phi1=p1, phi2=p2, c=0.0, noise=0.2, seed=2)
    _, phi2hat = fit_ar(x2, p=2)
    ck("fit_ar AR(2): phi1 recuperat (|d| < 0.05)", abs(phi2hat[0] - p1) < 0.05)
    ck("fit_ar AR(2): phi2 recuperat (|d| < 0.05)", abs(phi2hat[1] - p2) < 0.05)

    # ---- temporal_split pastreaza ordinea: max(train) < min(test), fara suprapunere
    s = np.arange(100.0)
    tr, te, itr, ite = temporal_split(s, train_frac=0.7)
    ck("temporal_split: 70 train + 30 test", tr.size == 70 and te.size == 30)
    ck("temporal_split: max(idx_train) < min(idx_test)", itr.max() < ite.min())
    ck("temporal_split: fara suprapunere de indici",
       len(set(itr.tolist()) & set(ite.tolist())) == 0)
    ck("temporal_split: acopera tot, in ordine",
       np.array_equal(np.concatenate([itr, ite]), np.arange(100)))
    ck("temporal_split: train pastreaza valorile cronologice", np.array_equal(tr, s[:70]))

    # ---- prognoza AR bate persistenta (RMSE mai mic) pe un proces AR
    xa = _ar1_process(800, phi=0.8, c=1.0, noise=0.4, seed=3)
    train, test, _, _ = temporal_split(xa, train_frac=0.75)
    c_f, phi_f = fit_ar(train, p=2)
    yt_ar, yp_ar = ar_predict_onestep(test, c_f, phi_f, warmup=train)
    yt_pe, yp_pe = persistence_forecast(train, test)
    rmse_ar = rmse(yt_ar, yp_ar)
    rmse_pe = rmse(yt_pe, yp_pe)
    print("    [info] RMSE AR = %.4f vs persistenta = %.4f" % (rmse_ar, rmse_pe))
    ck("forecast: AR bate persistenta (RMSE_AR < RMSE_persistenta)", rmse_ar < rmse_pe)

    # ---- forecast_ar multi-pas: lungime corecta + un-pas == predictie directa
    one = forecast_ar(train, c_f, phi_f, steps=1)
    ck("forecast_ar: un-pas are lungime 1", one.shape == (1,))
    multi = forecast_ar(train, c_f, phi_f, steps=5)
    ck("forecast_ar: multi-pas are lungimea ceruta", multi.shape == (5,))
    # un-pas direct == primul pas al prognozei pe test (acelasi warmup)
    ck("forecast_ar: un-pas == prima predictie pe test", abs(one[0] - yp_ar[0]) < 1e-9)

    print("\nTOATE VERIFICARILE serii_temporale_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
