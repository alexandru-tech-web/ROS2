#!/usr/bin/env python3
"""P3 -- Predictia deznodamantului misiunii (M04 + M12 + M13 + M14).

Ensemblu (Random Forest) pentru mission_complete, cu importanta de feature si
contrast fata de un singur arbore -- ce conditii prabusesc misiunea.

Date SINTETICE (din C1/M via date_sar). scikit-learn. Ruleaza in venv:
  /home/ubuntu/ros2_ws/.venv_ml/bin/python p3_deznodamant_misiune.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml
from date_sar import make_mission_outcome_dataset  # noqa: E402
from utils import maybe_savefig  # noqa: E402

from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.tree import DecisionTreeClassifier

FEATURES = ["delivered_frac", "p95_ms", "n_drones"]


def main():
    df = make_mission_outcome_dataset(n=800, seed=3)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["mission_complete"].to_numpy(dtype=int)
    print("=== P3: Predictia deznodamantului misiunii -- date SINTETICE ===")
    print("fractie misiuni reusite: %.3f" % y.mean())

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=0, stratify=y)
    tree = DecisionTreeClassifier(max_depth=3, random_state=0).fit(Xtr, ytr)
    rf = RandomForestClassifier(n_estimators=200, random_state=0).fit(Xtr, ytr)

    acc_tree = float(tree.score(Xte, yte))
    acc_rf = float(rf.score(Xte, yte))
    cv_rf = cross_val_score(rf, X, y, cv=5).mean()
    print("acuratete test -- arbore(d=3): %.3f | Random Forest: %.3f" % (acc_tree, acc_rf))
    print("acuratete RF 5-fold: %.3f" % cv_rf)

    imp = permutation_importance(rf, Xte, yte, n_repeats=20, random_state=0)
    ranks = sorted(zip(FEATURES, imp.importances_mean), key=lambda t: -t[1])
    print("importanta prin permutare:")
    for name, val in ranks:
        print("  %-15s %.4f" % (name, val))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 4))
        names = [n for n, _ in ranks]; vals = [v for _, v in ranks]
        ax.barh(names[::-1], vals[::-1])
        ax.set_title("P3 importanta feature (mission_complete) -- SINTETIC")
        maybe_savefig(fig, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig_p3_importanta.png"))
    except Exception as e:
        print("[fig] sarit:", e)

    assert acc_rf >= 0.5 and ranks[0][0] == "delivered_frac", \
        "RF ar trebui sa fie rezonabil si delivered_frac dominant"
    print("\nINTERPRETARE: fractia de telemetrie LIVRATA (delivered_frac) e factorul"
          " dominant al succesului misiunii -- coerent cu teza (livrarea, nu doar latenta,"
          " decide misiunea). Cifre pe date SINTETICE.")


if __name__ == "__main__":
    main()
