#!/usr/bin/env python3
"""P1 -- Pipeline de predictie a latentei (M04 + M05 + M06 + M07 + M18).

De la date brute la un model regularizat, validat corect: prezice log10(rtt_ms)
din feature-uri de netem/distanta + middleware, alege lambda Ridge prin validare
incrucisata, raporteaza RMSE fata de o baza (media) si un interval pe falduri.

Date SINTETICE (semanate din C1/M via date_sar). Foloseste scikit-learn pentru
pipeline (modulele predau versiunile de la zero). Ruleaza in venv:
  /home/ubuntu/ros2_ws/.venv_ml/bin/python p1_predictie_latenta.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml
from date_sar import make_latency_dataset  # noqa: E402
from utils import maybe_savefig  # noqa: E402

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUM = ["loss_pct", "base_lat_ms", "jitter_ms", "distance_m"]
CAT = ["middleware"]


def main():
    df = make_latency_dataset(n_per_cond=200, seed=0)
    X = df[NUM + CAT]
    y = np.log10(df["rtt_ms"].to_numpy(dtype=float))
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=0)

    pre = ColumnTransformer([("num", StandardScaler(), NUM),
                             ("cat", OneHotEncoder(), CAT)])
    pipe = Pipeline([("pre", pre), ("ridge", Ridge())])
    grid = GridSearchCV(pipe, {"ridge__alpha": [0.01, 0.1, 1.0, 10.0, 100.0]},
                        scoring="neg_root_mean_squared_error", cv=5)
    grid.fit(Xtr, ytr)
    best = grid.best_estimator_
    lam = grid.best_params_["ridge__alpha"]

    yhat = best.predict(Xte)
    rmse = float(np.sqrt(np.mean((yhat - yte) ** 2)))
    base = float(np.sqrt(np.mean((ytr.mean() - yte) ** 2)))   # baza: media de pe train
    cv_rmse = -cross_val_score(best, Xtr, ytr, cv=5,
                               scoring="neg_root_mean_squared_error")

    print("=== P1: Predictie latenta (log10 rtt_ms) -- date SINTETICE ===")
    print("lambda Ridge ales prin CV: %g" % lam)
    print("RMSE test (model): %.4f" % rmse)
    print("RMSE test (baza=media): %.4f" % base)
    print("castig fata de baza: %.1f%%" % (100 * (base - rmse) / base))
    print("RMSE 5-fold pe train: %.4f +/- %.4f (interval pe falduri)"
          % (cv_rmse.mean(), cv_rmse.std()))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(yte, yhat, s=8, alpha=0.4)
        lim = [min(yte.min(), yhat.min()), max(yte.max(), yhat.max())]
        ax.plot(lim, lim, "k--", lw=1)
        ax.set_xlabel("log10(rtt_ms) real"); ax.set_ylabel("prezis")
        ax.set_title("P1 predictie vs real (date SINTETICE)")
        maybe_savefig(fig, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig_p1_pred.png"))
    except Exception as e:
        print("[fig] sarit:", e)

    assert rmse < base, "modelul ar trebui sa bata baza"
    print("\nINTERPRETARE: modelul regularizat bate media cu o marja clara; lambda mic"
          " ales de CV arata ca semnalul (mai ales base_lat_ms) e puternic. Cifrele sunt"
          " pe date SINTETICE -- inlocuieste cu campania reala inainte de orice concluzie.")


if __name__ == "__main__":
    main()
