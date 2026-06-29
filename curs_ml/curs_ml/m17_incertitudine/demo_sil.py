#!/usr/bin/env python3
"""demo_sil.py -- M17: predictie cu interval de PREDICTIE pe datele mele de latenta.

Headless, fara argumente. Prezice log10(rtt_ms) din feature-uri standardizate cu o
regresie liniara bayesiana si raporteaza:
  - acoperirea empirica a intervalului de predictie 90%% pe un set de test;
  - intervalul de incredere bootstrap pe medie vs intervalul de predictie (banda mai
    larga = intervalul de predictie, fiindca include si zgomotul observatiei);
  - intervalul conformal split cu acoperire garantata.

ACCENTUL TEZEI (N mic): la N=5 o predictie fara bara de eroare e inutila. Aici banda
de incertitudine ARATA cat de mult sa crezi predictia.

Daca matplotlib exista, emite fig_incertitudine.png (predictie + banda de predictie
ordonata dupa o singura feature); altfel tipareste numeric.
Datele sunt SINTETICE (semanate din C1/M).
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
from utils import standardize, train_test_split, maybe_savefig  # noqa: E402

FEATURES = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]
LEVEL = 0.90
ALPHA = 1.0 - LEVEL


def main():
    df = make_latency_dataset(n_per_cond=120, seed=0)
    X = df[FEATURES].to_numpy(dtype=float)
    y = np.log10(df["rtt_ms"].to_numpy(dtype=float))

    # split train/test, standardizare CU statistici de pe TRAIN (fara scurgere)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_frac=0.30, seed=0)
    X_tr_s, X_te_s, mean, std = standardize(X_tr, X_te)

    # zgomotul observatiilor estimat din reziduurile OLS pe train
    y_hat_tr = _ols_fit_predict(X_tr_s, y_tr, X_tr_s)
    sig2 = float(np.var(y_tr - y_hat_tr))

    # ---- 1) interval de PREDICTIE bayesian
    blr = BayesianLinearRegression(lam=1e-3, sig2=sig2).fit(X_tr_s, y_tr)
    mean_p, lo_p, hi_p = blr.predict_interval(X_te_s, level=LEVEL)
    cov_pred = empirical_coverage(y_te, lo_p, hi_p)
    width_pred = float(np.mean(hi_p - lo_p))

    # ---- 2) interval de INCREDERE bootstrap (pe medie)
    mean_b, lo_b, hi_b = bootstrap_predict_interval(
        X_tr_s, y_tr, X_te_s, _ols_fit_predict, B=200, level=LEVEL, seed=1)
    width_boot = float(np.mean(hi_b - lo_b))

    # ---- 3) interval CONFORMAL split (acoperire garantata)
    # imparte train in propriu-zis-train + calibrare
    perm = np.random.default_rng(2).permutation(X_tr_s.shape[0])
    cut = X_tr_s.shape[0] // 2
    tr_i, cal_i = perm[:cut], perm[cut:]
    mean_c, lo_c, hi_c, q = conformal_split(
        X_tr_s[tr_i], y_tr[tr_i], X_tr_s[cal_i], y_tr[cal_i], X_te_s,
        _ols_fit_predict, alpha=ALPHA)
    cov_conf = empirical_coverage(y_te, lo_c, hi_c)
    width_conf = float(np.mean(hi_c - lo_c))

    print("Predictie log10(rtt_ms) cu incertitudine  (date SINTETICE, N_test=%d)" % len(y_te))
    print("nivel tinta: %.0f%%   (alpha=%.2f)" % (LEVEL * 100, ALPHA))
    print("-" * 64)
    print("  metoda                  acoperire_emp   latime_medie")
    print("  predictie bayesiana       %.3f           %.4f" % (cov_pred, width_pred))
    print("  incredere bootstrap       %s           %.4f  (pe MEDIE, nu predictie)"
          % ("  -  ", width_boot))
    print("  conformal split           %.3f           %.4f" % (cov_conf, width_conf))
    print("-" * 64)
    print("Observatie: banda de PREDICTIE (bayesiana, conformal) > banda de INCREDERE")
    print("(bootstrap), fiindca predictia include zgomotul unei observatii NOI.")

    # ---- figura: predictie + banda, ordonata dupa predictie (lizibil)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        order = np.argsort(mean_p)
        xs = np.arange(len(order))
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.fill_between(xs, lo_p[order], hi_p[order], alpha=0.25,
                        label="banda predictie %.0f%%" % (LEVEL * 100))
        ax.plot(xs, mean_p[order], lw=1.2, label="predictie (medie)")
        ax.plot(xs, y_te[order], ".", ms=4, label="adevar (test)")
        ax.set_xlabel("punct de test (ordonat dupa predictie)")
        ax.set_ylabel("log10(rtt_ms)")
        ax.set_title("Predictie cu bara de eroare (date SINTETICE) -- acoperire %.2f"
                     % cov_pred)
        ax.legend(loc="upper left", fontsize=8)
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_incertitudine.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
