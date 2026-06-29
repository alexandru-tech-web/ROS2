#!/usr/bin/env python3
"""demo_sil.py -- pipeline de feature engineering pe telemetria sintetica (M04).

Demonstratie headless, fara argumente. Construieste matricea de feature-uri pe
make_latency_dataset (telemetria sintetica semanata din C1/M):

  - tinta de regresie : rtt_ms (latenta dus-intors)
  - feature categoric : middleware (DDS / Zenoh)   -> ONE-HOT
  - feature-uri numerice: loss_pct, base_lat_ms, jitter_ms, distance_m -> Z-SCORE
    (standardizare cu media/abaterea invatate pe TRAIN, fara scurgere)

Pasii respecta regula de aur a M04: encoderul si scalerul se INVATA pe TRAIN si
se APLICA identic pe TEST. Daca matplotlib exista, emite figuri prin
utils.maybe_savefig; altfel tipareste numeric. Ruleaza fara crash cu:
  /home/ubuntu/ros2_ws/.venv_ml/bin/python demo_sil.py

ONESTITATE: datele NU sunt masuratori reale -- sunt SINTETICE, semanate din
campania C1 (p95 RTT / pierdere DDS vs Zenoh) si din modelul de canal M.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from date_features_core import (  # noqa: E402
    fit_one_hot, transform_one_hot, one_hot_feature_names,
    iqr_outlier_mask, polynomial_features,
)
from date_sar import make_latency_dataset  # noqa: E402
from utils import train_test_split, standardize, maybe_savefig  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
NUM_COLS = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]


def build_feature_matrix(df, ntr_frac=0.75, seed=0):
    """Construieste (F_tr, F_te, names, y_tr, y_te) cu one-hot + z-score, fara scurgere."""
    y = df["rtt_ms"].to_numpy(dtype=float)
    mid = df["middleware"].to_numpy()
    num = df[NUM_COLS].to_numpy(dtype=float)

    # split determinist pe indici (ca sa pastram aliniate categoricul si numericul)
    n = len(df)
    idx = np.arange(n)
    idx_tr, idx_te, _, _ = train_test_split(idx.reshape(-1, 1), idx, test_frac=1 - ntr_frac, seed=seed)
    itr = idx_tr.ravel().astype(int)
    ite = idx_te.ravel().astype(int)

    # one-hot pe middleware: vocabular invatat pe TRAIN
    cats = fit_one_hot(mid[itr])
    oh_tr = transform_one_hot(mid[itr], cats)
    oh_te = transform_one_hot(mid[ite], cats)

    # z-score pe numerice: stat invatate pe TRAIN
    num_tr_s, num_te_s, mean, std = standardize(num[itr], num[ite])

    F_tr = np.column_stack([oh_tr, num_tr_s])
    F_te = np.column_stack([oh_te, num_te_s])
    names = one_hot_feature_names(cats, prefix="mw") + ["z(%s)" % c for c in NUM_COLS]
    return F_tr, F_te, names, y[itr], y[ite], mean, std, cats


def main():
    print("=" * 70)
    print("M04 demo SIL -- feature engineering pe telemetrie SINTETICA (C1/M)")
    print("=" * 70)

    df = make_latency_dataset(n_per_cond=200, seed=0)
    print("Set brut: %d randuri, coloane: %s" % (len(df), list(df.columns)))
    print("Middleware (categoric): %s" % sorted(df["middleware"].unique().tolist()))
    print("Tinta de regresie: rtt_ms  (min=%.1f, mediana=%.1f, max=%.1f ms)" %
          (df.rtt_ms.min(), df.rtt_ms.median(), df.rtt_ms.max()))

    # ---- EDA scurt: outlieri pe rtt_ms via IQR (cozile lungi reale ale RTT) ----
    mask = iqr_outlier_mask(df["rtt_ms"].to_numpy(), k=1.5)
    print("\n[EDA] outlieri IQR pe rtt_ms: %d / %d (%.1f%%) -- cozile lungi din degradare"
          % (int(mask.sum()), len(df), 100.0 * mask.mean()))

    # ---- pipeline: one-hot middleware + z-score numerice (fara scurgere) ----
    F_tr, F_te, names, y_tr, y_te, mean, std, cats = build_feature_matrix(df)
    print("\n[pipeline] matrice de feature-uri:")
    print("  coloane (%d): %s" % (len(names), names))
    print("  F_train shape = %s ; F_test shape = %s" % (F_tr.shape, F_te.shape))
    print("  media z(numeric) pe TRAIN ~ 0: %s" % np.round(F_tr[:, 2:].mean(axis=0), 6).tolist())
    print("  abaterea z(numeric) pe TRAIN ~ 1: %s" % np.round(F_tr[:, 2:].std(axis=0), 6).tolist())
    print("  stat invatate pe TRAIN (mean numeric): %s" % np.round(mean, 3).tolist())
    print("  (aceleasi stat se aplica pe TEST -- fara scurgere)")

    print("\n[pipeline] primele 5 randuri din matricea de feature (TRAIN):")
    header = "  " + "  ".join("%9s" % nm[:9] for nm in names)
    print(header)
    for r in range(5):
        print("  " + "  ".join("%9.3f" % v for v in F_tr[r]))

    # ---- bonus: feature-uri polinomiale grad 2 pe numericele standardizate ----
    Ppoly, pnames = polynomial_features(F_tr[:, 2:], degree=2, include_bias=False)
    print("\n[poly] expansiune grad 2 pe cele %d numerice -> %d coloane (%s ...)"
          % (F_tr[:, 2:].shape[1], Ppoly.shape[1], pnames[:4]))

    # ---- figuri (daca matplotlib exista) ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # fig 1: distributia rtt_ms cu pragurile IQR
        x = df["rtt_ms"].to_numpy()
        q1, q3 = np.percentile(x, 25), np.percentile(x, 75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        fig1, ax1 = plt.subplots(figsize=(7, 4))
        ax1.hist(np.clip(x, 0, np.percentile(x, 99)), bins=60, color="#4477aa")
        ax1.axvline(hi, color="crimson", ls="--", label="prag sus IQR = %.0f ms" % hi)
        ax1.set_xlabel("rtt_ms (taiat la p99 pentru lizibilitate)")
        ax1.set_ylabel("frecventa")
        ax1.set_title("M04: distributie rtt_ms + prag outlieri IQR (date sintetice C1/M)")
        ax1.legend()
        maybe_savefig(fig1, os.path.join(HERE, "fig_rtt_iqr.png"))

        # fig 2: heatmap al matricei de feature (primele 40 randuri)
        fig2, ax2 = plt.subplots(figsize=(7, 5))
        im = ax2.imshow(F_tr[:40], aspect="auto", cmap="viridis")
        ax2.set_xticks(range(len(names)))
        ax2.set_xticklabels(names, rotation=45, ha="right", fontsize=7)
        ax2.set_ylabel("rand (esantion TRAIN)")
        ax2.set_title("M04: matrice de feature (one-hot mw + z-score numeric)")
        fig2.colorbar(im, ax=ax2, label="valoare feature")
        maybe_savefig(fig2, os.path.join(HERE, "fig_feature_matrix.png"))
    except Exception as e:  # pragma: no cover - depinde de mediu
        print("\n[fig] matplotlib indisponibil sau eroare la desen: %s" % e)
        print("[fig] raport numeric mai sus este suficient (rulare headless).")

    print("\nGata. Pipeline: EDA -> one-hot (middleware) -> z-score (numeric, TRAIN->TEST).")
    return None


if __name__ == "__main__":
    main()
