#!/usr/bin/env python3
"""demo_sil.py -- M05 pe datele tezei: prezice rtt_ms din feature-uri de retea.

Sarcina (legatura cu teza): din feature-urile unei legaturi degradate
  - base_lat_ms   (latenta de baza injectata de netem),
  - loss_pct      (rata de pierdere [%]),
  - distance_m    (distanta nod-nod),
  - middleware    (DDS vs Zenoh, codificat 0/1 -> mw_zenoh),
prezicem timpul dus-intors rtt_ms. Antrenam regresia liniara prin ecuatiile
normale (nucleul nostru), pe feature-uri standardizate, si o comparam cu o BAZA
triviala: a prezice mereu media rtt_ms din train.

ONESTITATE: datele vin din date_sar.make_latency_dataset si sunt SINTETICE
(semanate din campania C1). RTT-ul real e puternic ne-gaussian (cozi lungi), deci
prezicem log10(rtt_ms) -- regresia liniara se potriveste mult mai bine pe scara
logaritmica (vezi teorie.md, capcane). Raportam RMSE/R^2 pe scara originala [ms].

Headless, fara argumente. Daca matplotlib exista, scrie fig_*.png; altfel numeric.
Ruleaza: python3 demo_sil.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import maybe_savefig, r2_score, rmse, standardize, train_test_split  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402
from regresie_liniara_core import RegresieLiniara, numar_conditie  # noqa: E402

FEATURES = ["base_lat_ms", "loss_pct", "distance_m", "mw_zenoh"]


def build_xy(df):
    """Construieste matricea de feature-uri X si tinta y=log10(rtt_ms)."""
    d = df.copy()
    d["mw_zenoh"] = (d["middleware"] == "Zenoh").astype(float)
    X = d[FEATURES].to_numpy(dtype=float)
    y_ms = d["rtt_ms"].to_numpy(dtype=float)
    y_log = np.log10(np.clip(y_ms, 1e-3, None))
    return X, y_log, y_ms


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    df = make_latency_dataset(n_per_cond=200, seed=0)
    print("Date: make_latency_dataset (SINTETICE, semanate din C1). N =", len(df))
    print("Feature-uri:", FEATURES, "-> tinta: log10(rtt_ms)")

    X, y_log, y_ms = build_xy(df)
    Xtr, Xte, ytr_log, yte_log = train_test_split(X, y_log, test_frac=0.30, seed=0)
    # tinem si rtt-ul brut [ms] aliniat la acelasi split (pentru raport pe scara ms)
    _, _, ytr_ms, yte_ms = train_test_split(X, y_ms, test_frac=0.30, seed=0)

    # standardizare cu statistici de pe TRAIN (fara scurgere)
    Xtr_s, Xte_s, _, _ = standardize(Xtr, Xte)

    print("\nNumar de conditie X^T X (cu bias):")
    print("  feature-uri brute       : %.3e" % numar_conditie(np.column_stack(
        [np.ones(len(Xtr)), Xtr])))
    print("  feature-uri standardizate: %.3e" % numar_conditie(np.column_stack(
        [np.ones(len(Xtr_s)), Xtr_s])))

    # ---- model liniar prin ecuatii normale
    model = RegresieLiniara(method="normal").fit(Xtr_s, ytr_log)
    yhat_log = model.predict(Xte_s)
    yhat_ms = np.power(10.0, yhat_log)  # inapoi pe scara [ms]

    # ---- baza: media rtt-ului (in spatiul log, apoi inapoi pe ms)
    base_log = np.full_like(yte_log, ytr_log.mean())
    base_ms = np.power(10.0, base_log)

    # rapoarte pe scara originala [ms]
    rmse_model = rmse(yte_ms, yhat_ms)
    rmse_base = rmse(yte_ms, base_ms)
    r2_model = r2_score(yte_ms, yhat_ms)
    r2_base = r2_score(yte_ms, base_ms)
    # si pe scara log (unde modelul e liniar)
    r2_log = r2_score(yte_log, yhat_log)

    print("\n--- Rezultate pe TEST (scara originala [ms]) ---")
    print("  RMSE model  : %10.2f ms" % rmse_model)
    print("  RMSE baza   : %10.2f ms   (prezice media)" % rmse_base)
    print("  R^2  model  : %10.4f" % r2_model)
    print("  R^2  baza   : %10.4f" % r2_base)
    print("  R^2  model (pe scara log10): %.4f" % r2_log)
    castig = 100.0 * (1.0 - rmse_model / rmse_base) if rmse_base > 0 else 0.0
    print("  reducere RMSE fata de baza : %.1f%%" % castig)

    # coeficienti interpretabili (pe feature standardizat: marime = importanta)
    w = model.w_
    print("\nCoeficienti (model standardizat, tinta log10 rtt):")
    print("  intercept            : %+.4f" % w[0])
    for name, coef in zip(FEATURES, w[1:]):
        print("  %-20s : %+.4f" % (name, coef))

    # ---- figura prezis vs real (daca matplotlib exista)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
        # (a) prezis vs real pe scara log10 [ms]
        ax[0].scatter(yte_log, yhat_log, s=10, alpha=0.4, color="tab:blue")
        lo = min(yte_log.min(), yhat_log.min())
        hi = max(yte_log.max(), yhat_log.max())
        ax[0].plot([lo, hi], [lo, hi], "r--", lw=1.2, label="identitate")
        ax[0].set_xlabel("log10(rtt_ms) real")
        ax[0].set_ylabel("log10(rtt_ms) prezis")
        ax[0].set_title("Prezis vs real (R^2_log = %.3f)" % r2_log)
        ax[0].legend(loc="upper left")
        # (b) RMSE model vs baza [ms]
        ax[1].bar(["model liniar", "baza (media)"], [rmse_model, rmse_base],
                  color=["tab:green", "tab:gray"])
        ax[1].set_ylabel("RMSE [ms]")
        ax[1].set_title("Eroare pe test: model vs baza")
        for i, v in enumerate([rmse_model, rmse_base]):
            ax[1].text(i, v, "%.0f" % v, ha="center", va="bottom")
        fig.suptitle("M05 regresie liniara -- predictie rtt_ms (date SINTETICE C1)")
        fig.tight_layout()
        maybe_savefig(fig, os.path.join(here, "fig_pred_vs_real.png"))
    except Exception as e:  # pragma: no cover - depinde de mediu
        print("\n[fig] matplotlib indisponibil sau eroare (%s); doar numeric." % e)

    print("\nConcluzie: pe scara log, feature-urile de retea explica bine rtt_ms")
    print("(R^2_log ridicat) si modelul bate clar baza care prezice media.")
    return 0


if __name__ == "__main__":
    main()
