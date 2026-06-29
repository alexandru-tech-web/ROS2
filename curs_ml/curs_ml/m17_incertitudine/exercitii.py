#!/usr/bin/env python3
"""exercitii.py -- M17 Cuantificarea incertitudinii (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul incertitudine_core.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from incertitudine_core import (  # noqa: E402
    BayesianLinearRegression, bootstrap_predict_interval, conformal_split,
    empirical_coverage, _ols_fit_predict,
)
from date_sar import make_latency_dataset  # noqa: E402
from utils import standardize  # noqa: E402

FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]


# ---------------------------------------------------------------- Ex.1
def ex1_posterior_1d(x, y, lam, sig2):
    """E1. Regresie liniara bayesiana 1D FARA bias, de mana (un singur parametru w).

    Cu phi(x)=x (scalar) si N puncte (x_i, y_i), posteriorul pe w este gaussian cu:
        S = 1 / (lam + (1/sig2) * sum x_i^2)
        m = (1/sig2) * S * sum x_i*y_i
    Returneaza (m, S) ca float-uri. NU folosi BayesianLinearRegression.
    (Vezi exemplul lucrat din teorie.md, sectiunea 5.)
    """
    # TODO: aplica formulele de mai sus pe array-urile x, y
    raise NotImplementedError("E1: posterior bayesian 1D")


# ---------------------------------------------------------------- Ex.2
def ex2_contractie_posterior(lam, sig2):
    """E2. Arata ca posteriorul se CONTRACTA cu mai multe date.

    Genereaza date liniare 1D (foloseste rng-ul de mai jos), antreneaza
    BayesianLinearRegression pe 10 puncte si pe 500 de puncte, intoarce
    (trace_mic, trace_mare) = urma covariantei posterioare in cele doua cazuri.
    Asteptare: trace_mare < trace_mic.
    """
    rng = np.random.default_rng(0)
    Xa = rng.uniform(-3, 3, size=(10, 1))
    ya = 1.0 + 2.0 * Xa[:, 0] + 0.4 * rng.standard_normal(10)
    Xb = rng.uniform(-3, 3, size=(500, 1))
    yb = 1.0 + 2.0 * Xb[:, 0] + 0.4 * rng.standard_normal(500)
    # TODO: antreneaza doua modele si intoarce (cov_trace mic, cov_trace mare)
    raise NotImplementedError("E2: contractia posteriorului")


# ---------------------------------------------------------------- Ex.3
def ex3_acoperire_predictie(level):
    """E3. Acoperirea empirica a intervalului de PREDICTIE bayesian.

    Genereaza date liniare 1D (rng de mai jos), antreneaza un model bayesian, cere
    intervalul de predictie la `level` pe setul de test si intoarce acoperirea
    empirica (fractia de tinte de test in interval). Foloseste empirical_coverage.
    Asteptare: acoperirea >= level - 0.05.
    """
    rng = np.random.default_rng(1)
    X_tr = rng.uniform(-3, 3, size=(150, 1))
    y_tr = -1.0 + 2.0 * X_tr[:, 0] + 0.5 * rng.standard_normal(150)
    X_te = rng.uniform(-3, 3, size=(2000, 1))
    y_te = -1.0 + 2.0 * X_te[:, 0] + 0.5 * rng.standard_normal(2000)
    # TODO: fit BayesianLinearRegression(lam=1e-3, sig2=0.25), predict_interval,
    #       apoi empirical_coverage
    raise NotImplementedError("E3: acoperirea intervalului de predictie")


# ---------------------------------------------------------------- Ex.4
def ex4_conformal_acoperire(alpha):
    """E4. Conformal split: acoperire empirica pe test >= 1 - alpha - toleranta.

    Genereaza date (rng de mai jos), imparte train in train+calibrare (jumatate-
    jumatate), aplica conformal_split cu _ols_fit_predict si intoarce acoperirea
    empirica pe test. Asteptare: >= 1 - alpha - 0.03.
    """
    rng = np.random.default_rng(2)
    X = rng.uniform(-3, 3, size=(400, 1))
    y = 0.5 + 1.5 * X[:, 0] + 0.6 * rng.standard_normal(400)
    X_te = rng.uniform(-3, 3, size=(2000, 1))
    y_te = 0.5 + 1.5 * X_te[:, 0] + 0.6 * rng.standard_normal(2000)
    n = X.shape[0]
    perm = rng.permutation(n)
    cut = n // 2
    tr, cal = perm[:cut], perm[cut:]
    # TODO: conformal_split(X[tr], y[tr], X[cal], y[cal], X_te, _ols_fit_predict, alpha)
    #       apoi empirical_coverage(y_te, lo, hi)
    raise NotImplementedError("E4: acoperirea conformal")


# ---------------------------------------------------------------- Ex.5
def ex5_predictie_vs_incredere():
    """E5. Pe datele mele de latenta: banda de PREDICTIE > banda de INCREDERE.

    Pe make_latency_dataset(n_per_cond=80, seed=0), feature-uri standardizate ->
    log10(rtt_ms): calculeaza latimea medie a intervalului de predictie bayesian
    (level 0.90) si latimea medie a intervalului de incredere bootstrap (level 0.90,
    B=100) pe acelasi set. Returneaza (latime_predictie, latime_incredere).
    Asteptare: latime_predictie > latime_incredere.
    """
    df = make_latency_dataset(n_per_cond=80, seed=0)
    X = df[FEATURES].to_numpy(dtype=float)
    y = np.log10(df["rtt_ms"].to_numpy(dtype=float))
    Xs, _, _, _ = standardize(X)
    # TODO: fit BayesianLinearRegression, predict_interval -> latime predictie;
    #       bootstrap_predict_interval -> latime incredere; intoarce ambele latimi
    raise NotImplementedError("E5: predictie vs incredere")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # E1: caz mic verificabil de mana. x=[1,2], y=[2,4], lam=0, sig2=1.
    # S = 1/(0 + (1^2+2^2)) = 1/5 ; m = (1/1)*S*(1*2+2*4)=10/5=2.0
    m, S = ex1_posterior_1d([1.0, 2.0], [2.0, 4.0], lam=0.0, sig2=1.0)
    ck("E1: S = 1/5", abs(S - 0.2) < 1e-12)
    ck("E1: m = 2.0", abs(m - 2.0) < 1e-12)

    tmic, tmare = ex2_contractie_posterior(lam=1e-3, sig2=0.16)
    ck("E2: posteriorul se contracta (trace mare < trace mic)", tmare < tmic)

    cov = ex3_acoperire_predictie(level=0.90)
    ck("E3: acoperire predictie >= 0.85", cov >= 0.85)

    covc = ex4_conformal_acoperire(alpha=0.1)
    ck("E4: acoperire conformal >= 0.87", covc >= 0.87)

    wp, wi = ex5_predictie_vs_incredere()
    ck("E5: banda de predictie > banda de incredere", wp > wi)

    print("\nTOATE EXERCITIILE M17 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
