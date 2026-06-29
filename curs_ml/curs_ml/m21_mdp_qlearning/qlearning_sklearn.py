#!/usr/bin/env python3
"""qlearning_sklearn.py -- validare incrucisata a nucleului M21.

ATENTIE (documentat onest): scikit-learn NU contine invatare prin recompensa
tabulara (nici Q-learning, nici iteratie pe valoare). Nu exista o referinta
sklearn de comparat cap la cap. In LOC, validam INCRUCISAT politica invatata de
Q-learning fata de REFERINTA ANALITICA din chiar nucleul nostru -- iteratia pe
valoare (programare dinamica), care rezolva exact ecuatia Bellman de optimalitate.

Adica: pe mai multe MDP-uri ALEATOARE mici, verificam ca politica greedy invatata
de Q-learning (model-free, doar din tranzitii esantionate) coincide cu politica
optima data de value_iteration (care foloseste P si R direct). Daca cele doua cai
-- una stocastica si model-free, alta deterministica si bazata pe model -- ajung la
ACEEASI politica, ne increde ca implementarea Q-learning e corecta. Aceasta e
echivalentul de 'validare incrucisata' pentru un domeniu fara echivalent sklearn.

Pastram interfata fratilor *_sklearn.py (sys.exit(0/1)) si un try/except inofensiv
in jurul importului de sklearn (doar ca sa raportam ca, daca ar fi cerut, lipseste
sensul -- nu blocheaza nimic).

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python qlearning_sklearn.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from qlearning_core import (  # noqa: E402
    MDP, value_iteration, q_learning, greedy_policy, policy_values,
)

# sklearn nu ajuta la RL tabular; importul e doar ca sa documentam absenta unei
# referinte si sa pastram forma fratilor *_sklearn.py (nu e o eroare daca lipseste).
try:
    import sklearn  # noqa: F401
    _HAVE_SK = True
except ImportError:
    _HAVE_SK = False


def random_mdp(nS, nA, gamma, rng):
    """Un MDP mic ALEATOR: tranzitii dintr-o Dirichlet (rare, deci dependente
    nebanale de stare) si recompense uniforme. Tinem MDP-ul mic ca value_iteration
    si Q-learning sa convearga sigur la aceeasi politica (fara legaturi aproape
    egale care fac argmax-ul instabil)."""
    P = rng.dirichlet(np.ones(nS) * 0.5, size=(nS, nA))   # (nS, nA, nS), suma 1 pe s'
    R = rng.uniform(-2.0, 10.0, size=(nS, nA, nS))
    return MDP(P, R, gamma)


def _value_gap_rel(mdp, pi_learned, V_star):
    """Cat de departe de OPTIM e politica invatata, ca VALOARE RELATIVA (scalata,
    deci independenta de marimea recompenselor):

        max_s ( V*(s) - V_pi_learned(s) ) / max_s |V*(s)|

    Zero <=> politica e optima. Metrica onesta: pe MDP-uri aleatoare apar legaturi
    (doua actiuni aproape egale), unde eticheta argmax poate diferi fara ca valoarea
    sa difere semnificativ -- conteaza valoarea, nu eticheta."""
    V_pi = policy_values(mdp, pi_learned)
    scale = max(1e-9, float(np.max(np.abs(V_star))))
    return float(np.max(V_star - V_pi)) / scale


def _check():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    if not _HAVE_SK:
        print("[sklearn] indisponibil -- oricum nu are RL tabular; continui cu "
              "referinta analitica (value_iteration).")
    else:
        print("[nota] scikit-learn nu are RL tabular; validez fata de "
              "programarea dinamica (value_iteration), nu fata de sklearn.")

    # Validare incrucisata pe MAI MULTE MDP-uri aleatoare mici: politica Q-learning
    # atinge VALOAREA optima data de value_iteration (programare dinamica).
    rng = np.random.default_rng(0)
    n_mdps = 8
    n_exact = 0          # politici identice ca ETICHETA
    val_gaps = []        # golul de VALOARE invatat-vs-optim (metrica onesta)
    for i in range(n_mdps):
        nS = int(rng.integers(2, 5))     # 2..4 stari
        nA = int(rng.integers(2, 4))     # 2..3 actiuni
        gamma = float(rng.uniform(0.8, 0.95))
        mdp = random_mdp(nS, nA, gamma, rng)

        V_star, _, pi_star = value_iteration(mdp)
        Q = q_learning(mdp, n_episodes=4000, max_steps=30, alpha=1.0,
                       epsilon=0.3, seed=100 + i, alpha_decay=0.7)
        pi_q = greedy_policy(Q)

        if np.array_equal(pi_q, pi_star):
            n_exact += 1
        val_gaps.append(_value_gap_rel(mdp, pi_q, V_star))

    max_gap = max(val_gaps)
    # Golul de VALOARE RELATIV e criteriul onest de convergenta: pe legaturi (actiuni
    # aproape egale) eticheta poate diferi cu cost de valoare neglijabil (< 1%).
    ck("Q-learning atinge valoarea optima pe toate MDP-urile (gol relativ < 1%)",
       max_gap < 0.01)
    # Si pe majoritatea, chiar si ETICHETA politicii coincide exact cu optimul.
    ck("politica Q-learning == optim ca eticheta pe majoritatea MDP-urilor (>= 3/4)",
       n_exact >= int(np.ceil(0.75 * n_mdps)))

    print("\nVALIDARE INCRUCISATA M21 OK (fata de programare dinamica): "
          "%d/%d politici identice ca eticheta, gol de valoare relativ max %.4f pe %d MDP-uri."
          % (n_exact, n_mdps, max_gap, n_mdps))
    return ok


if __name__ == "__main__":
    try:
        _check()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
