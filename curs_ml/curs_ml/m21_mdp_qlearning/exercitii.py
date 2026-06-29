#!/usr/bin/env python3
"""exercitii.py -- M21 MDP si Q-learning (STUB-URI cu TODO).

Completeaza fiecare functie marcata cu TODO. Rulat ACUM trebuie sa PICE (exit != 0).
Solutiile complete in solutii.py. Refoloseste nucleul qlearning_core.

MDP-ul de comutare e un MODEL SINTETIC (vezi qlearning_core.py).

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python exercitii.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from qlearning_core import (  # noqa: E402
    make_link_switch_mdp, value_iteration, q_learning, greedy_policy,
    average_episode_reward,
)


# ---------------------------------------------------------------- Ex.1
def ex1_discounted_return(rewards, gamma):
    """E1. Return-ul cu discount G = r_1 + gamma r_2 + gamma^2 r_3 + ... pentru un
    sir de recompense. Returneaza un float.
    """
    # TODO: insumeaza gamma**t * rewards[t] pentru t = 0, 1, 2, ...
    raise NotImplementedError("E1: return cu discount")


# ---------------------------------------------------------------- Ex.2
def ex2_q_update(q_sa, r, gamma, alpha, q_next_row):
    """E2. O actualizare Q-learning. q_sa = Q(s,a) curent; q_next_row = Q(s', :).
    Aplica  Q(s,a) <- Q(s,a) + alpha [ r + gamma max_a' Q(s',a') - Q(s,a) ]  si
    returneaza noul Q(s,a) (float). (Vezi exemplul numeric din teorie.md.)
    """
    # TODO
    raise NotImplementedError("E2: o actualizare Q de mana")


# ---------------------------------------------------------------- Ex.3
def ex3_greedy_policy(Q):
    """E3. Politica greedy fata de tabelul Q (forma (nS, nA)): argmax pe fiecare
    rand. Returneaza un array de nS actiuni. NU folosi greedy_policy din nucleu.
    """
    # TODO: foloseste numpy.argmax pe axa actiunilor
    raise NotImplementedError("E3: politica greedy")


# ---------------------------------------------------------------- Ex.4
def ex4_optimal_policy():
    """E4. Pe mediul de comutare (make_link_switch_mdp), ruleaza value_iteration si
    intoarce politica optima ca LISTA de NUME de actiuni (mdp.action_names).
    Asteptare: ["DDS", "Zenoh", "Zenoh"].
    """
    # TODO
    raise NotImplementedError("E4: politica optima prin iteratie pe valoare")


# ---------------------------------------------------------------- Ex.5
def ex5_learned_beats_static():
    """E5. Pe mediul de comutare: antreneaza Q-learning (n_episodes=5000,
    max_steps=40, alpha=1.0, epsilon=0.3, seed=0, alpha_decay=0.7), ia politica
    greedy invatata si compara recompensa medie pe episod cu cea mai buna politica
    STATICA (mereu DDS = actiunea 0, mereu Zenoh = actiunea 1).
    Foloseste average_episode_reward(..., n_episodes=400, max_steps=40, seed=123).
    Returneaza (r_invatat, r_cea_mai_buna_statica).
    """
    # TODO
    raise NotImplementedError("E5: invatat vs static")


# ---------------------------------------------------------------- verificare
def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    g = ex1_discounted_return([1.0, 1.0, 1.0], 0.5)
    ck("E1: return cu discount pe [1,1,1], gamma=0.5 = 1.75", abs(g - 1.75) < 1e-12)

    q = ex2_q_update(2.0, 10.0, 0.9, 0.5, [3.0, 5.0])
    ck("E2: actualizare Q de mana da 8.25", abs(q - 8.25) < 1e-12)

    pol = ex3_greedy_policy(np.array([[5.0, 1.0], [1.0, 5.0], [2.0, 3.0]]))
    ck("E3: politica greedy = [0, 1, 1]", list(np.asarray(pol)) == [0, 1, 1])

    popt = ex4_optimal_policy()
    ck("E4: politica optima = [DDS, Zenoh, Zenoh]",
       list(popt) == ["DDS", "Zenoh", "Zenoh"])

    r_lnd, r_stat = ex5_learned_beats_static()
    ck("E5: politica invatata nu pierde fata de cea mai buna statica",
       r_lnd >= r_stat - 1e-6)

    print("\nTOATE EXERCITIILE M21 REZOLVATE: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except (AssertionError, NotImplementedError) as e:
        print("PICA (asteptat pana rezolvi): %s" % e)
        sys.exit(1)
