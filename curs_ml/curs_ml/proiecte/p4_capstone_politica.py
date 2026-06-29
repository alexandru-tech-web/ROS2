#!/usr/bin/env python3
"""P4 (capstone) -- Politica adaptiva vs statica (M17/M19 + M21 + M22).

Inchide cursul in teza (C3): (1) antreneaza predictorul de stare a linkului din
M22; (2) invata o politica de comutare DDS/Zenoh ca MDP cu Q-learning (M21);
(3) compara politica INVATATA cu cele STATICE (mereu DDS / mereu Zenoh) si cu
optimul (value iteration). Figura comparativa pentru un articol A2.

Foloseste nucleele reale M21 si M22 (numpy pur). Date/recompense SINTETICE
(model semanat din C1/M). Ruleaza in venv:
  /home/ubuntu/ros2_ws/.venv_ml/bin/python p4_capstone_politica.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)                       # .../curs_ml/curs_ml
sys.path.insert(0, PKG)
sys.path.insert(0, os.path.join(PKG, "m21_mdp_qlearning"))
sys.path.insert(0, os.path.join(PKG, "m22_capstone_link_predictor"))

from date_sar import make_link_usability_dataset  # noqa: E402
from utils import maybe_savefig  # noqa: E402
from qlearning_core import (make_link_switch_mdp, value_iteration, q_learning,  # noqa: E402
                            greedy_policy, average_episode_reward)
from link_predictor_core import train_from_dataset, FEATURE_NAMES  # noqa: E402


def main():
    print("=== P4 capstone: predictor de link + politica adaptiva vs statica ===")
    print("    (nuclee reale M21 + M22; date/recompense SINTETICE din C1/M)\n")

    # (1) Predictorul de stare a linkului (M22)
    df = make_link_usability_dataset(n_per_cond=200, seed=1)
    n = len(df); cut = int(0.75 * n)
    pred = train_from_dataset(df.iloc[:cut], feature_names=FEATURE_NAMES, label="usable")
    te = df.iloc[cut:]
    yhat = np.array([pred.predict(row[FEATURE_NAMES].to_dict())[0] for _, row in te.iterrows()])
    acc = float(np.mean(yhat == te["usable"].to_numpy()))
    print("[M22] predictor de link: acuratete test = %.3f" % acc)

    # (2) Politica de comutare ca MDP (M21)
    mdp = make_link_switch_mdp()
    nS = np.asarray(mdp.P).shape[0]
    V_star, Q_star, pi_star = value_iteration(mdp)
    Q_learned = q_learning(mdp, n_episodes=4000)
    if isinstance(Q_learned, tuple):
        Q_learned = Q_learned[0]
    pi_learned = greedy_policy(Q_learned)

    pol_dds = np.zeros(nS, dtype=int)     # mereu actiunea 0 (DDS)
    pol_zen = np.ones(nS, dtype=int)      # mereu actiunea 1 (Zenoh)

    def R(policy):
        return average_episode_reward(mdp, policy, n_episodes=300, max_steps=40, seed=1)

    r_learn, r_dds, r_zen, r_opt = R(pi_learned), R(pol_dds), R(pol_zen), R(pi_star)
    best_static = max(r_dds, r_zen)
    print("\n[M21] recompensa medie pe episod (mai mare = mai bine):")
    print("  mereu DDS    : %.3f" % r_dds)
    print("  mereu Zenoh  : %.3f" % r_zen)
    print("  INVATATA     : %.3f" % r_learn)
    print("  optim (VI)   : %.3f" % r_opt)
    print("  castig politica invatata fata de cea mai buna statica: %+.1f%%"
          % (100 * (r_learn - best_static) / abs(best_static)))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4))
        labels = ["mereu DDS", "mereu Zenoh", "invatata", "optim"]
        vals = [r_dds, r_zen, r_learn, r_opt]
        ax.bar(labels, vals, color=["#999", "#999", "#2a7", "#27a"])
        ax.set_ylabel("recompensa medie / episod")
        ax.set_title("P4 politica adaptiva vs statica (date SINTETICE)")
        maybe_savefig(fig, os.path.join(HERE, "fig_p4_politica.png"))
    except Exception as e:
        print("[fig] sarit:", e)

    assert r_learn >= best_static - 1e-6, "politica invatata nu ar trebui sa fie sub cea statica"
    assert r_learn <= r_opt + 1e-6, "politica invatata nu poate depasi optimul"
    print("\nINTERPRETARE (C3): politica adaptiva invatata atinge ~optimul si bate cea mai"
          " buna alegere statica de middleware -- exact teza C3 (link_adaptive). Predictorul"
          " M22 ofera starea de link consumabila de nod. Recompensele sunt SINTETICE/model;"
          " concluzia se confirma cu date HIL si o dinamica temporala reala (vezi nota M21).")


if __name__ == "__main__":
    main()
