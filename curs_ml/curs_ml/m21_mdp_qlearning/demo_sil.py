#!/usr/bin/env python3
"""demo_sil.py -- M21: comutarea QoS/middleware ca MDP, invatata cu Q-learning.

Headless, fara argumente. Pune in scena PUNTEA catre contributia C3 a tezei:
modeleaza alegerea middleware-ului (DDS vs Zenoh) pe un link care isi schimba
conditia (GOOD / DEGRADED / BAD) ca un proces de decizie Markov, antreneaza un
agent Q-learning si compara recompensa politicii INVATATE cu doua politici STATICE
(mereu DDS / mereu Zenoh). Raporteaza castigul.

Daca matplotlib exista, emite fig_invatare_qlearning.png (recompensa pe episod vs
antrenare); altfel tipareste numeric.

ONESTITATE (vezi CLAUDE.md sec.0): MDP-ul de comutare e un MODEL SINTETIC --
tranzitiile si recompensele (valoare de misiune) sunt alese de mana, calibrate dupa
intuitia campaniei C1 (DDS bun pe link curat, Zenoh mai rezistent la degradare),
NU masurate. De inlocuit cu un MDP estimat din date HIL inainte de orice articol.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from qlearning_core import (  # noqa: E402
    make_link_switch_mdp, value_iteration, q_learning, greedy_policy,
    average_episode_reward, policy_values,
)
from utils import maybe_savefig  # noqa: E402


def _smooth(x, w=100):
    """Medie alunecatoare pentru curba de invatare (vizibilitate)."""
    if x.size < w:
        return x
    return np.convolve(x, np.ones(w) / w, mode="valid")


def main():
    mdp = make_link_switch_mdp(gamma=0.9)
    names = mdp.action_names
    snames = mdp.state_names

    # referinta optima (programare dinamica) -- ce ar putea atinge un agent perfect
    V_star, _, pi_star = value_iteration(mdp)
    print("MDP de comutare a legaturii (MODEL SINTETIC -- vezi antet).")
    print("  stari   :", snames)
    print("  actiuni :", names)
    print("  politica OPTIMA (value_iteration):",
          [names[a] for a in pi_star])

    # antrenare Q-learning (model-free)
    Q, rewards = q_learning(mdp, n_episodes=5000, max_steps=40, alpha=1.0,
                            epsilon=0.3, seed=0, alpha_decay=0.7, return_history=True)
    pi_learned = greedy_policy(Q)
    print("  politica INVATATA (Q-learning)   :",
          [names[a] for a in pi_learned])

    # comparatie de recompensa pe episod: invatata vs statice (mereu DDS / mereu Zenoh)
    EVAL_KW = dict(n_episodes=400, max_steps=40, seed=123)
    r_learned = average_episode_reward(mdp, pi_learned, **EVAL_KW)
    r_dds = average_episode_reward(mdp, np.zeros(mdp.nS, dtype=int), **EVAL_KW)   # mereu DDS
    r_zen = average_episode_reward(mdp, np.ones(mdp.nS, dtype=int), **EVAL_KW)    # mereu Zenoh
    r_opt = average_episode_reward(mdp, pi_star, **EVAL_KW)

    print("\nRecompensa medie pe episod (40 pasi, MODEL SINTETIC):")
    print("  mereu DDS (static)   : %8.2f" % r_dds)
    print("  mereu Zenoh (static) : %8.2f" % r_zen)
    print("  Q-learning (invatat) : %8.2f" % r_learned)
    print("  optim (value_iter)   : %8.2f" % r_opt)
    best_static = max(r_dds, r_zen)
    gain = r_learned - best_static
    gain_pct = 100.0 * gain / abs(best_static) if abs(best_static) > 1e-9 else 0.0
    which = "DDS" if r_dds >= r_zen else "Zenoh"
    print("\nCASTIG comutare-invatata vs cea mai buna statica (mereu %s): "
          "%+.2f (%+.1f%%)" % (which, gain, gain_pct))

    # valori pe stare (programare dinamica) pentru context
    V_learned = policy_values(mdp, pi_learned)
    print("\nValoarea pe stare (V), politica invatata vs optim:")
    for s in range(mdp.nS):
        print("  %-9s  invatat %7.2f   optim %7.2f" % (snames[s], V_learned[s], V_star[s]))

    # figura: curba de invatare (recompensa pe episod, netezita)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        sm = _smooth(rewards, w=100)
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(np.arange(sm.size), sm, label="Q-learning (medie alunecatoare 100)")
        ax.axhline(r_opt, color="green", ls="--", label="optim (value iteration)")
        ax.axhline(best_static, color="gray", ls=":", label="cea mai buna statica (mereu %s)" % which)
        ax.set_xlabel("episod de antrenare")
        ax.set_ylabel("recompensa pe episod")
        ax.set_title("Comutare QoS/middleware ca MDP -- invatare (date SINTETICE)")
        ax.legend(loc="lower right")
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_invatare_qlearning.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
