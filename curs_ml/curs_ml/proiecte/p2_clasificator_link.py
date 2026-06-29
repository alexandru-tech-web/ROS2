#!/usr/bin/env python3
"""P2 -- Clasificator de link 'usable' calibrat si explicat (M04 + M08 + M09 + M14).

Pe clase DEZECHILIBRATE: antreneaza un clasificator pentru 'usable', alege pragul
pe recall-ul clasei rare, calibreaza probabilitatile si explica feature-urile prin
importanta de permutare.

Date SINTETICE (din C1/M via date_sar). scikit-learn pentru pipeline. Ruleaza in venv:
  /home/ubuntu/ros2_ws/.venv_ml/bin/python p2_clasificator_link.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml
from date_sar import make_link_usability_dataset  # noqa: E402
from utils import maybe_savefig  # noqa: E402

from sklearn.calibration import CalibratedClassifierCV
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["p95_ms", "loss_frac", "jitter_ms", "base_lat_ms", "distance_m"]


def main():
    df = make_link_usability_dataset(n_per_cond=200, seed=1)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["usable"].to_numpy(dtype=int)
    print("=== P2: Clasificator link usable (DEZECHILIBRAT) -- date SINTETICE ===")
    print("fractie usable (clasa rara): %.3f" % y.mean())

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=0, stratify=y)
    clf = make_pipeline(StandardScaler(),
                        LogisticRegression(class_weight="balanced", max_iter=1000))
    clf.fit(Xtr, ytr)
    proba = clf.predict_proba(Xte)[:, 1]
    ap = average_precision_score(yte, proba)
    print("average precision (PR-AUC): %.3f" % ap)

    # prag pentru recall-tinta 0.9 pe clasa rara
    prec, rec, thr = precision_recall_curve(yte, proba)
    target = 0.90
    ok = np.where(rec[:-1] >= target)[0]
    thr_sel = float(thr[ok[-1]]) if len(ok) else 0.5
    pred_sel = (proba >= thr_sel).astype(int)
    print("prag pentru recall>=%.2f: %.3f -> recall realizat %.3f"
          % (target, thr_sel, recall_score(yte, pred_sel)))

    # calibrare
    cal = CalibratedClassifierCV(clf, method="isotonic", cv=3).fit(Xtr, ytr)
    proba_cal = cal.predict_proba(Xte)[:, 1]
    # importanta prin permutare
    imp = permutation_importance(clf, Xte, yte, n_repeats=20, random_state=0,
                                 scoring="average_precision")
    ranks = sorted(zip(FEATURES, imp.importances_mean), key=lambda t: -t[1])
    print("importanta prin permutare (PR-AUC):")
    for name, val in ranks:
        print("  %-12s %.4f" % (name, val))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
        a1.plot(rec, prec); a1.set_xlabel("recall"); a1.set_ylabel("precizie")
        a1.set_title("Curba PR (AP=%.3f)" % ap)
        names = [n for n, _ in ranks]; vals = [v for _, v in ranks]
        a2.barh(names[::-1], vals[::-1]); a2.set_title("Importanta prin permutare")
        fig.suptitle("P2 link usable (date SINTETICE)")
        maybe_savefig(fig, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig_p2_pr.png"))
    except Exception as e:
        print("[fig] sarit:", e)

    assert ap > 0.5, "PR-AUC ar trebui sa bata aleatorul"
    print("\nINTERPRETARE: pe clase dezechilibrate, pragul se alege pe recall-ul clasei"
          " rare (nu pe acuratete). Feature-ul dominant (de obicei p95_ms / loss) explica"
          " utilizabilitatea. Cifre pe date SINTETICE.")


if __name__ == "__main__":
    main()
