#!/usr/bin/env python3
"""solutii.py -- M21 MDP si Q-learning (SOLUTIILE complete). Ruleaza -> exit 0."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from qlearning_core import (  # noqa: E402
    make_link_switch_mdp, value_iteration, q_learning, greedy_policy,
    average_episode_reward,
)


def ex1_discounted_return(rewards, gamma):
    r = np.asarray(rewards, dtype=float)
    disc = gamma ** np.arange(r.size)
    return float(np.sum(disc * r))


def ex2_q_update(q_sa, r, gamma, alpha, q_next_row):
    best_next = float(np.max(q_next_row))
    td_error = r + gamma * best_next - q_sa
    return float(q_sa + alpha * td_error)


def ex3_greedy_policy(Q):
    return np.asarray(Q).argmax(axis=1)


def ex4_optimal_policy():
    mdp = make_link_switch_mdp(gamma=0.9)
    _, _, pi = value_iteration(mdp)
    return [mdp.action_names[a] for a in pi]


def ex5_learned_beats_static():
    mdp = make_link_switch_mdp(gamma=0.9)
    Q = q_learning(mdp, n_episodes=5000, max_steps=40, alpha=1.0,
                   epsilon=0.3, seed=0, alpha_decay=0.7)
    pi = greedy_policy(Q)
    kw = dict(n_episodes=400, max_steps=40, seed=123)
    r_learned = average_episode_reward(mdp, pi, **kw)
    r_dds = average_episode_reward(mdp, np.zeros(mdp.nS, dtype=int), **kw)
    r_zen = average_episode_reward(mdp, np.ones(mdp.nS, dtype=int), **kw)
    return r_learned, max(r_dds, r_zen)


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    ck("E1: return discount [1,1,1] g=0.5 = 1.75",
       abs(ex1_discounted_return([1.0, 1.0, 1.0], 0.5) - 1.75) < 1e-12)
    ck("E2: actualizare Q = 8.25",
       abs(ex2_q_update(2.0, 10.0, 0.9, 0.5, [3.0, 5.0]) - 8.25) < 1e-12)
    ck("E3: politica greedy = [0,1,1]",
       list(ex3_greedy_policy(np.array([[5.0, 1.0], [1.0, 5.0], [2.0, 3.0]]))) == [0, 1, 1])
    ck("E4: politica optima = [DDS, Zenoh, Zenoh]",
       ex4_optimal_policy() == ["DDS", "Zenoh", "Zenoh"])
    r_lnd, r_stat = ex5_learned_beats_static()
    ck("E5: invatat >= cea mai buna statica", r_lnd >= r_stat - 1e-6)

    print("\nTOATE SOLUTIILE M21 TREC: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
