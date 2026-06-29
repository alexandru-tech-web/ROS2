#!/usr/bin/env python3
"""solutii.py -- M05 regresie liniara. Solutiile complete (separate de stub-uri).

Rulat cu venv trebuie sa TREACA (exit 0). Date SINTETICE (semanate din C1/M).
Ruleaza: python3 solutii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import add_bias, r2_score, rmse, standardize, train_test_split  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402
from regresie_liniara_core import fit_normal_equations, numar_conditie, predict  # noqa: E402

FEATURES = ["base_lat_ms", "loss_pct", "distance_m", "mw_zenoh"]


def _xy(df, features=FEATURES):
    d = df.copy()
    d["mw_zenoh"] = (d["middleware"] == "Zenoh").astype(float)
    X = d[features].to_numpy(dtype=float)
    y_ms = d["rtt_ms"].to_numpy(dtype=float)
    y_log = np.log10(np.clip(y_ms, 1e-3, None))
    return X, y_log, y_ms


# ---------------------------------------------------------------- Ex. 1
def ex1_castig_fata_de_baza():
    df = make_latency_dataset(n_per_cond=200, seed=0)
    X, y_log, y_ms = _xy(df)
    Xtr, Xte, ytr, yte = train_test_split(X, y_log, test_frac=0.30, seed=0)
    _, _, _, yte_ms = train_test_split(X, y_ms, test_frac=0.30, seed=0)
    Xtr_s, Xte_s, _, _ = standardize(Xtr, Xte)
    w = fit_normal_equations(add_bias(Xtr_s), ytr)
    yhat_ms = np.power(10.0, predict(add_bias(Xte_s), w))
    base_ms = np.power(10.0, np.full_like(yte, ytr.mean()))
    rmse_model = rmse(yte_ms, yhat_ms)
    rmse_base = rmse(yte_ms, base_ms)
    return 100.0 * (1.0 - rmse_model / rmse_base)


# ---------------------------------------------------------------- Ex. 2
def ex2_ecuatii_normale_de_mana():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    y = np.array([2.0, 2.0, 4.0, 4.0])
    w = fit_normal_equations(add_bias(x.reshape(-1, 1)), y)
    return float(w[0]), float(w[1])


# ---------------------------------------------------------------- Ex. 3
def ex3_gradient_descent(X, y, alpha=0.2, n_iter=20000):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    n, d = X.shape
    w = np.zeros(d)
    for _ in range(int(n_iter)):
        resid = X @ w - y
        grad = (2.0 / n) * (X.T @ resid)
        w = w - alpha * grad
    return w


# ---------------------------------------------------------------- Ex. 4
def ex4_conditionare():
    df = make_latency_dataset(n_per_cond=200, seed=0)
    X, _, _ = _xy(df)
    cond_brut = numar_conditie(add_bias(X))
    Xs, _, _, _ = standardize(X)
    cond_std = numar_conditie(add_bias(Xs))
    return cond_brut, cond_std


# ---------------------------------------------------------------- Ex. 5
def ex5_r2_per_middleware():
    feats = ["base_lat_ms", "loss_pct", "distance_m"]  # fara mw_zenoh
    df = make_latency_dataset(n_per_cond=200, seed=0)
    out = {}
    for mw in ("DDS", "Zenoh"):
        sub = df[df.middleware == mw]
        X, y_log, _ = _xy(sub, features=feats)
        Xtr, Xte, ytr, yte = train_test_split(X, y_log, test_frac=0.30, seed=0)
        Xtr_s, Xte_s, _, _ = standardize(Xtr, Xte)
        w = fit_normal_equations(add_bias(Xtr_s), ytr)
        yhat = predict(add_bias(Xte_s), w)
        out[mw] = r2_score(yte, yhat)
    return out


# ---------------------------------------------------------------- Ex. 6
def _r2_log_test(X, y_log):
    Xtr, Xte, ytr, yte = train_test_split(X, y_log, test_frac=0.30, seed=0)
    Xtr_s, Xte_s, _, _ = standardize(Xtr, Xte)
    w = fit_normal_equations(add_bias(Xtr_s), ytr)
    return r2_score(yte, predict(add_bias(Xte_s), w))


def ex6_feature_distanta_patrat():
    df = make_latency_dataset(n_per_cond=200, seed=0)
    X, y_log, _ = _xy(df)
    r2_baza = _r2_log_test(X, y_log)
    X_ext = np.column_stack([X, X[:, FEATURES.index("distance_m")] ** 2])
    r2_extins = _r2_log_test(X_ext, y_log)
    return r2_baza, r2_extins


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    ck("ex1: castig > 20%", ex1_castig_fata_de_baza() > 20.0)

    w0, w1 = ex2_ecuatii_normale_de_mana()
    ck("ex2: (w0,w1) ~ (1.0, 0.8)", abs(w0 - 1.0) < 1e-6 and abs(w1 - 0.8) < 1e-6)

    g = np.random.default_rng(0)
    Xr = g.normal(0, 1, size=(200, 3))
    yr = 1.0 + Xr @ np.array([2.0, -1.0, 0.5]) + g.normal(0, 0.3, size=200)
    Xs, _, _, _ = standardize(Xr)
    Xb = add_bias(Xs)
    w_ne = fit_normal_equations(Xb, yr)
    w_gd = ex3_gradient_descent(Xb, yr, alpha=0.2, n_iter=20000)
    ck("ex3: gradient descent ~ ecuatii normale (||.|| < 1e-3)",
       np.linalg.norm(w_gd - w_ne) < 1e-3)

    cb, cs = ex4_conditionare()
    ck("ex4: standardizarea reduce conditionarea > 100x", cs < cb / 100.0)

    r2d = ex5_r2_per_middleware()
    ck("ex5: R^2 DDS si Zenoh > 0.3 (scara log)",
       r2d["DDS"] > 0.3 and r2d["Zenoh"] > 0.3)

    r2_b, r2_e = ex6_feature_distanta_patrat()
    ck("ex6: feature in plus nu strica (>= baza - 0.01)", r2_e >= r2_b - 0.01)

    print("\nTOATE SOLUTIILE TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        print("PASS")
        sys.exit(0)
    except AssertionError as e:
        print(e)
        print("FAIL")
        sys.exit(1)
