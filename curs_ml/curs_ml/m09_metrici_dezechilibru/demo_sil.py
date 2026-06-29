#!/usr/bin/env python3
"""demo_sil.py -- M09: metrici, dezechilibru si calibrare pe datele mele de link.

Headless, fara argumente. Pe make_link_usability_dataset (clase DEZECHILIBRATE,
'usable' minoritar ~30%) antrenam un clasificator simplu (o regresie logistica
MINIMALA proprie, in numpy, chiar in acest fisier -- demo AUTO-SUFICIENT, fara
import din alte module de model), apoi:
  - raportam acuratetea (care MINTE la dezechilibru), AUC-ROC si precizia medie;
  - alegem pragul dupa recall-ul clasei RARE (usable) si aratam ce castigam fata
    de pragul implicit 0.5;
  - calibram scorurile cu scalare Platt si masuram ECE inainte/dupa;
  - daca matplotlib exista, emitem fig_pr_calibrare.png (curba PR + diagrama de
    calibrare); altfel tiparim numeric.

Datele sunt SINTETICE (semanate din C1/M via date_sar.py).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from metrici_calibrare_core import (  # noqa: E402
    roc_auc, pr_curve, average_precision, threshold_for_recall,
    reliability_curve, expected_calibration_error, platt_fit, platt_predict,
)
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import standardize, accuracy, precision_recall_f1, maybe_savefig  # noqa: E402

FEATURES = ["p95_ms", "loss_frac", "jitter_ms", "base_lat_ms", "mw_zenoh", "distance_m"]


# -------- regresie logistica minimala, proprie (numpy pur), DOAR pentru demo ----
def _logreg_fit(X, y, lr=0.2, n_iter=4000, l2=1e-3, seed=0):
    """Regresie logistica binara prin gradient descendent determinist (cu bias si
    regularizare L2 usoara). Auto-suficienta -- nu importa din m08."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    n, d = X.shape
    rng = np.random.default_rng(seed)
    w = rng.normal(0, 0.01, d)
    b = 0.0
    for _ in range(n_iter):
        z = X @ w + b
        p = 1.0 / (1.0 + np.exp(-z))
        err = p - y
        gw = X.T @ err / n + l2 * w
        gb = float(np.mean(err))
        w -= lr * gw
        b -= lr * gb
    return w, b


def _logreg_proba(X, w, b):
    z = np.asarray(X, dtype=float) @ w + b
    return 1.0 / (1.0 + np.exp(-z))


def main():
    df = make_link_usability_dataset(n_per_cond=120, seed=1)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["usable"].to_numpy(dtype=int)

    # split determinist train/test (fara stratificare -- vezi nota din teorie.md)
    perm = np.random.default_rng(0).permutation(len(y))
    n_te = int(round(0.30 * len(y)))
    te, tr = perm[:n_te], perm[n_te:]
    Xtr_s, Xte_s, _, _ = standardize(X[tr], X[te])

    base_rate = float(y.mean())
    print("clasa rara 'usable': %.1f%% din date (DEZECHILIBRU)" % (100.0 * base_rate))

    w, b = _logreg_fit(Xtr_s, y[tr], seed=0)
    s_te = _logreg_proba(Xte_s, w, b)
    yt = y[te]

    # acuratetea MINTE: comparam cu clasificatorul majoritar (prezice mereu 0)
    acc_model = accuracy(yt, (s_te >= 0.5).astype(int))
    acc_majoritar = accuracy(yt, np.zeros_like(yt))
    auc = roc_auc(yt, s_te)
    ap = average_precision(yt, s_te)
    print("acuratete model (prag 0.5): %.3f" % acc_model)
    print("acuratete 'prezice mereu inutilizabil': %.3f  <- de ce acuratetea minte" % acc_majoritar)
    print("AUC-ROC: %.3f   precizie medie (AP): %.3f" % (auc, ap))

    # prag implicit 0.5 vs prag ales pe recall-ul clasei rare
    prec0, rec0, f10 = precision_recall_f1(yt, (s_te >= 0.5).astype(int))
    thr_r, rec_r = threshold_for_recall(yt, s_te, target_recall=0.90)
    prec_r, rec_r2, f1_r = precision_recall_f1(yt, (s_te >= thr_r).astype(int))
    print("prag 0.5      -> precizie %.3f  recall %.3f  F1 %.3f" % (prec0, rec0, f10))
    print("prag %.3f (recall>=0.90) -> precizie %.3f  recall %.3f  F1 %.3f"
          % (thr_r, prec_r, rec_r2, f1_r))

    # calibrare: ECE pe scoruri brute vs dupa Platt
    ece_raw = expected_calibration_error(yt, s_te, n_bins=8)
    params = platt_fit(s_te, yt, lr=0.5, n_iter=4000, seed=0)
    s_cal = platt_predict(s_te, params)
    ece_cal = expected_calibration_error(yt, s_cal, n_bins=8)
    print("ECE scoruri brute: %.4f   ECE dupa Platt: %.4f" % (ece_raw, ece_cal))

    # curba PR (numeric)
    precision, recall, _ = pr_curve(yt, s_te)
    print("curba PR (cateva puncte): precizie / recall")
    for i in np.linspace(0, len(recall) - 1, min(5, len(recall))).astype(int):
        print("  P=%.3f  R=%.3f" % (precision[i], recall[i]))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

        ax1.plot(recall, precision, marker=".", linestyle="-")
        ax1.axhline(base_rate, color="gray", linestyle="--", label="precizie de baza (rata pozitivilor)")
        ax1.set_xlabel("recall"); ax1.set_ylabel("precizie")
        ax1.set_title("Curba PR (AP=%.3f)" % ap); ax1.set_ylim(0, 1.02); ax1.legend()

        mp_raw, fp_raw, _ = reliability_curve(yt, s_te, n_bins=8)
        mp_cal, fp_cal, _ = reliability_curve(yt, s_cal, n_bins=8)
        ax2.plot([0, 1], [0, 1], color="gray", linestyle="--", label="perfect calibrat")
        ax2.plot(mp_raw, fp_raw, marker="o", label="brut (ECE=%.3f)" % ece_raw)
        ax2.plot(mp_cal, fp_cal, marker="s", label="Platt (ECE=%.3f)" % ece_cal)
        ax2.set_xlabel("probabilitate medie pe bin"); ax2.set_ylabel("frecventa reala")
        ax2.set_title("Diagrama de calibrare"); ax2.set_xlim(0, 1); ax2.set_ylim(0, 1); ax2.legend()

        fig.suptitle("M09 -- metrici la dezechilibru si calibrare (date SINTETICE)")
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_pr_calibrare.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
