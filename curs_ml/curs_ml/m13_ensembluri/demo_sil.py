#!/usr/bin/env python3
"""demo_sil.py -- M13: un singur ciot vs bagging vs boosting pe mission_complete.

Headless, fara argumente. Prezice mission_complete (misiune SAR reusita) din
(delivered_frac, p95_ms, n_drones) cu trei modele construite de la zero in
ensembluri_core: un singur ciot de decizie, bagging si gradient boosting. Compara
acuratetea prin validare incrucisata k-fold (medie +/- abatere) -- arata cum
ensemblurile bat invatatorul slab de baza.

Daca matplotlib exista, emite fig_ensembluri.png cu (1) acuratetea CV a celor trei
modele si (2) curba de eroare a boosting-ului vs numarul de pasi (capcana
supra-invatarii). Altfel tipareste numeric.

Datele sunt SINTETICE (semanate din C1/M via date_sar.py).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from ensembluri_core import (  # noqa: E402
    DecisionStump, BaggingClassifier, GradientBoostingClassifier, _sigmoid,
)
from date_sar import make_mission_outcome_dataset  # noqa: E402
from utils import accuracy, maybe_savefig  # noqa: E402

FEATURES = ["delivered_frac", "p95_ms", "n_drones"]


def _kfold(n, k, seed=0):
    """Indici k-fold amestecati determinist: lista de (train_idx, test_idx)."""
    idx = np.random.default_rng(seed).permutation(n)
    folds = np.array_split(idx, k)
    out = []
    for i in range(k):
        te = folds[i]
        tr = np.concatenate([folds[j] for j in range(k) if j != i])
        out.append((tr, te))
    return out


def _cv_accuracy(make_model, X, y, k=5, seed=0):
    """Acuratete CV (medie, abatere) a unui model construit de make_model()."""
    scores = []
    for tr, te in _kfold(X.shape[0], k, seed=seed):
        m = make_model().fit(X[tr], y[tr])
        scores.append(accuracy(y[te], np.asarray(m.predict(X[te])).astype(int)))
    s = np.array(scores)
    return float(s.mean()), float(s.std(ddof=1))


def main():
    df = make_mission_outcome_dataset(n=600, seed=3)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["mission_complete"].to_numpy(dtype=int)
    print("mission_complete: %d/%d pozitive (%.1f%%)" %
          (y.sum(), len(y), 100.0 * y.mean()))

    models = [
        ("un singur ciot", lambda: DecisionStump(task="clf")),
        ("bagging (51 cioturi)", lambda: BaggingClassifier(n_estimators=51, seed=0)),
        ("boosting (60 pasi, lr=0.3)",
         lambda: GradientBoostingClassifier(n_estimators=60, learning_rate=0.3)),
    ]
    print("\nmodel                          acuratete CV 5-fold")
    means = []
    names = []
    for name, mk in models:
        mu, sd = _cv_accuracy(mk, X, y, k=5, seed=0)
        print("  %-28s %.4f +/- %.4f" % (name, mu, sd))
        means.append(mu)
        names.append(name.split(" (")[0])

    # curba de eroare a boosting-ului vs numarul de pasi (train vs test)
    perm = np.random.default_rng(0).permutation(len(y))
    cut = int(0.75 * len(y))
    tr, te = perm[:cut], perm[cut:]
    gb = GradientBoostingClassifier(n_estimators=120, learning_rate=0.3).fit(X[tr], y[tr])
    Ftr = gb.staged_decision_function(X[tr])
    Fte = gb.staged_decision_function(X[te])
    steps = np.arange(1, len(Ftr) + 1)
    err_tr = [1.0 - accuracy(y[tr], (_sigmoid(F) >= 0.5).astype(int)) for F in Ftr]
    err_te = [1.0 - accuracy(y[te], (_sigmoid(F) >= 0.5).astype(int)) for F in Fte]
    print("\nboosting -- eroare vs pasi (cateva puncte):")
    for s in (1, 10, 30, 60, 120):
        i = s - 1
        print("  pasi=%3d  train_err=%.3f  test_err=%.3f" % (s, err_tr[i], err_te[i]))
    print("  (eroarea de test se aseaza/creste cand cea de train scade -> supra-invatare)")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
        ax1.bar(names, means, color=["#999999", "#4c72b0", "#c44e52"])
        ax1.set_ylim(0.5, 1.0)
        ax1.set_ylabel("acuratete CV 5-fold")
        ax1.set_title("Ciot vs bagging vs boosting")
        for i, m in enumerate(means):
            ax1.text(i, m + 0.005, "%.3f" % m, ha="center")
        ax2.plot(steps, err_tr, label="train", color="#4c72b0")
        ax2.plot(steps, err_te, label="test", color="#c44e52")
        ax2.set_xlabel("numar de pasi de boosting")
        ax2.set_ylabel("eroare 0/1")
        ax2.set_title("Boosting: capcana supra-invatarii")
        ax2.legend()
        fig.suptitle("M13 ensembluri pe mission_complete (date SINTETICE)")
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_ensembluri.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
