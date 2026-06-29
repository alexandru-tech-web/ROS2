#!/usr/bin/env python3
"""exercitii.py -- M05 regresie liniara. STUB-URI cu TODO.

Completeaza fiecare functie acolo unde scrie TODO. Pana atunci, aserturile din
__main__ PICA (clar, cu mesaj) -- e corect: ruleaza-l acum si trebuie sa pice.
Verifica-ti raspunsurile ruland 'solutii.py' (acela trebuie sa treaca, exit 0).

Date SINTETICE (semanate din C1/M via date_sar). Determinism prin seed.
Ruleaza: python3 exercitii.py
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
    """Antreneaza regresia liniara (ecuatii normale) pe log10(rtt_ms) si intoarce
    reducerea procentuala a RMSE [ms] fata de baza (prezice media). > 20%."""
    # TODO: construieste X, y_log, y_ms cu _xy(make_latency_dataset(...))
    # TODO: split train/test (test_frac=0.30, seed=0) pe (X, y_log) si pe (X, y_ms)
    # TODO: standardizeaza cu utils.standardize(Xtr, Xte)
    # TODO: fit_normal_equations pe add_bias(Xtr_s); prezice -> inapoi pe ms (10**)
    # TODO: baza = media y_log de pe train -> inapoi pe ms; RMSE ambele pe ms
    # TODO: intoarce 100*(1 - rmse_model/rmse_base)
    raise NotImplementedError("TODO ex1")


# ---------------------------------------------------------------- Ex. 2
def ex2_ecuatii_normale_de_mana():
    """Exemplul din teorie: x=[1,2,3,4], y=[2,2,4,4] -> (w0, w1) ~ (1.0, 0.8)."""
    # TODO: x, y ca mai sus; X = add_bias(x.reshape(-1,1))
    # TODO: w = fit_normal_equations(X, y); intoarce (w[0], w[1])
    raise NotImplementedError("TODO ex2")


# ---------------------------------------------------------------- Ex. 3
def ex3_gradient_descent(X, y, alpha=0.2, n_iter=20000):
    """Coborare pe gradient de la zero: w <- w - alpha*(2/n) X^T (Xw - y).
    Returneaza w (X include deja bias-ul)."""
    # TODO: n = X.shape[0]; w = np.zeros(X.shape[1])
    # TODO: bucla n_iter: resid = X@w - y; grad = (2/n)*X.T@resid; w -= alpha*grad
    # TODO: intoarce w
    raise NotImplementedError("TODO ex3")


# ---------------------------------------------------------------- Ex. 4
def ex4_conditionare():
    """(cond_brut, cond_std) pentru X^T X cu bias, brut vs standardizat."""
    # TODO: X = feature-urile din make_latency_dataset
    # TODO: cond_brut = numar_conditie(add_bias(X))
    # TODO: Xs,_,_,_ = standardize(X); cond_std = numar_conditie(add_bias(Xs))
    # TODO: intoarce (cond_brut, cond_std)
    raise NotImplementedError("TODO ex4")


# ---------------------------------------------------------------- Ex. 5
def ex5_r2_per_middleware():
    """{'DDS': r2, 'Zenoh': r2} pe scara log, model separat per middleware,
    feature-uri fara mw_zenoh. Ambele > 0.3."""
    # TODO: pentru fiecare mw in ('DDS','Zenoh'): filtreaza df, _xy fara mw_zenoh
    # TODO: split, standardize, fit, predict; r2 pe scara log pe test
    raise NotImplementedError("TODO ex5")


# ---------------------------------------------------------------- Ex. 6
def ex6_feature_distanta_patrat():
    """(r2_baza, r2_extins) pe scara log, test; extins adauga distance_m^2.
    r2_extins >= r2_baza - 0.01."""
    # TODO: construieste baza (FEATURES) si extins (FEATURES + distance_m^2)
    # TODO: acelasi split/standardize/fit; intoarce (r2_baza, r2_extins)
    raise NotImplementedError("TODO ex6")


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

    # ex3 vs ecuatii normale pe date standardizate
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

    print("\nTOATE EXERCITIILE REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        print("PASS")
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("INCA NEREZOLVAT (asteptat pana completezi TODO):", e)
        sys.exit(1)
