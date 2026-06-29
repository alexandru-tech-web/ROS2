#!/usr/bin/env python3
"""qlearning_core.py -- nucleul M21, numpy pur (scikit-learn nefolosit -- nici nu
are RL tabular).

Procese de decizie Markov (MDP) si Q-learning tabular, de la zero:
  - clasa MDP: stari, actiuni, tensorul de tranzitie P[s,a,s'], recompensa
    R[s,a,s'] (asteptata pe (s,a) prin medie ponderata cu P), factor de discount
    gamma, si un esantionator `step(s, a, rng)` pentru episoade;
  - make_link_switch_mdp(): mediul de comutare a legaturii. Starile sunt conditii
    de link (GOOD / DEGRADED / BAD), actiunile sunt middleware-ul ales pe pasul
    urmator (DDS / Zenoh), recompensa este o VALOARE DE MISIUNE (mare cand linkul
    e bun si alegerea e potrivita, negativa cand linkul cade). ASTA E PUNTEA catre
    contributia C3 a tezei: comutarea QoS/middleware ca MDP.
  - value_iteration(): referinta OPTIMA prin programare dinamica (ecuatia Bellman
    de optimalitate). Da V*, Q* si politica greedy pi*.
  - q_learning(): invatare tabulara, model-free, epsilon-greedy, din tranzitii
    esantionate. NU foloseste P sau R direct -- doar (s, a, r, s') ca un agent real.
  - greedy_policy(): politica greedy fata de un tabel Q.

ONESTITATE (vezi CHARTA.md, CLAUDE.md sec.0): MDP-ul de comutare e un MODEL
SINTETIC. Tranzitiile si recompensele sunt alese de mana sa fie interpretabile
si calibrate dupa intuitia campaniei C1 (DDS bun pe link curat, Zenoh mai rezistent
la degradare), NU masurate. Serveste invatarii si punerii in scena a lui C3.

Determinism: tot aleatorul trece prin numpy.random.default_rng(seed).

_selftest() verifica:
  - Q-learning converge la politica OPTIMA a unui MDP mic CUNOSCUT
    (politica invatata == politica din value_iteration);
  - la convergenta, valorile satisfac ecuatia Bellman (reziduu Bellman mic);
  - recompensa cumulata pe episod CRESTE cu antrenarea;
  - epsilon-greedy cu epsilon > 0 viziteaza TOATE actiunile in fiecare stare.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python qlearning_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

# (utils nu e necesar aici: nucleul RL e auto-suficient pe numpy. Importul de mai
#  sus pastreaza conventia de cale a cursului pentru frate-le sklearn/demo.)


# ============================================================ MDP
class MDP(object):
    """Proces de decizie Markov finit (stari si actiuni discrete).

    P : array (nS, nA, nS), P[s,a,s'] = probabilitatea s -> s' sub actiunea a.
        Fiecare P[s,a,:] insumeaza 1.
    R : array (nS, nA, nS), R[s,a,s'] = recompensa primita la tranzitia s -a-> s'.
    gamma : factor de discount in [0, 1).
    Numele de stari/actiuni sunt doar pentru afisare/interpretare.
    """

    def __init__(self, P, R, gamma, state_names=None, action_names=None):
        P = np.asarray(P, dtype=float)
        R = np.asarray(R, dtype=float)
        if P.ndim != 3 or P.shape != R.shape:
            raise ValueError("P si R trebuie sa aiba aceeasi forma (nS, nA, nS)")
        nS, nA, nS2 = P.shape
        if nS != nS2:
            raise ValueError("P trebuie (nS, nA, nS); primit %r" % (P.shape,))
        if not np.allclose(P.sum(axis=2), 1.0):
            raise ValueError("fiecare P[s,a,:] trebuie sa insumeze 1")
        if not 0.0 <= gamma < 1.0:
            raise ValueError("gamma trebuie in [0, 1), primit %r" % (gamma,))
        self.P = P
        self.R = R
        self.gamma = float(gamma)
        self.nS = nS
        self.nA = nA
        self.state_names = list(state_names) if state_names else list(range(nS))
        self.action_names = list(action_names) if action_names else list(range(nA))

    def expected_reward(self):
        """Recompensa asteptata r(s,a) = sum_s' P[s,a,s'] R[s,a,s'] -> (nS, nA)."""
        return np.einsum("sap,sap->sa", self.P, self.R)

    def step(self, s, a, rng):
        """Esantioneaza o tranzitie: intoarce (s_next, reward) pornind din (s, a)."""
        s_next = int(rng.choice(self.nS, p=self.P[s, a]))
        reward = float(self.R[s, a, s_next])
        return s_next, reward


# ============================================================ MEDIUL DE COMUTARE
def make_link_switch_mdp(gamma=0.9):
    """MDP-ul de comutare a legaturii -- PUNTEA catre C3 (MODEL SINTETIC).

    Stari (conditii de link, din spiritul campaniei C1):
      0 = GOOD     (link curat: RTT mic, fara pierdere)
      1 = DEGRADED (degradare moderata: latenta/jitter, pierdere mica)
      2 = BAD      (degradare severa: pierdere mare, deadline-uri ratate)
    Actiuni (middleware-ul ales pentru intervalul urmator):
      0 = DDS   (rmw_cyclonedds_cpp -- supus mai bun pe link curat)
      1 = Zenoh (rmw_zenoh_cpp     -- mai rezistent la degradare)

    Recompensa = VALOARE DE MISIUNE pe interval: mare cand ramane in GOOD, modesta
    in DEGRADED, negativa in BAD. Alegerea middleware-ului inclina si tranzitiile
    (Zenoh recupereaza mai des din degradare) si recompensa.

    Politica optima INTUITIVA: DDS in GOOD, Zenoh in DEGRADED si BAD -- comuti pe
    middleware-ul rezistent exact cand linkul se strica. value_iteration o confirma.
    """
    nS, nA = 3, 2
    P = np.zeros((nS, nA, nS))
    R = np.zeros((nS, nA, nS))

    # ---- GOOD (s=0): link curat. DDS ramane mai des in GOOD si livreaza mai mult.
    P[0, 0] = [0.8, 0.2, 0.0]; R[0, 0] = [10.0, 4.0, 0.0]   # DDS
    P[0, 1] = [0.7, 0.3, 0.0]; R[0, 1] = [8.0, 4.0, 0.0]    # Zenoh (overhead mic)

    # ---- DEGRADED (s=1): Zenoh recupereaza mai des, scapa mai rar in BAD.
    P[1, 0] = [0.3, 0.4, 0.3]; R[1, 0] = [6.0, 2.0, -2.0]   # DDS
    P[1, 1] = [0.5, 0.4, 0.1]; R[1, 1] = [6.0, 3.0, -2.0]   # Zenoh

    # ---- BAD (s=2): linkul e in genunchi; Zenoh il scoate mai des spre DEGRADED.
    P[2, 0] = [0.0, 0.3, 0.7]; R[2, 0] = [0.0, 0.0, -6.0]   # DDS (rar revine)
    P[2, 1] = [0.0, 0.6, 0.4]; R[2, 1] = [0.0, 1.0, -4.0]   # Zenoh

    return MDP(P, R, gamma,
               state_names=["GOOD", "DEGRADED", "BAD"],
               action_names=["DDS", "Zenoh"])


# ============================================================ VALUE ITERATION (referinta)
def value_iteration(mdp, tol=1e-10, max_iter=10000):
    """Iteratie pe valoare: rezolva ecuatia Bellman de optimalitate prin
    programare dinamica (FOLOSESTE P si R -- referinta optima, nu model-free).

        Q*(s,a) = sum_s' P[s,a,s'] ( R[s,a,s'] + gamma V*(s') )
        V*(s)   = max_a Q*(s,a)

    Returneaza (V*, Q*, pi*) cu pi* = argmax_a Q*(s,a)."""
    P, R, gamma = mdp.P, mdp.R, mdp.gamma
    V = np.zeros(mdp.nS)
    Q = np.zeros((mdp.nS, mdp.nA))
    for _ in range(max_iter):
        # Q[s,a] = sum_s' P[s,a,s'] (R[s,a,s'] + gamma V[s'])
        Q = np.einsum("sap,sap->sa", P, R + gamma * V[None, None, :])
        V_new = Q.max(axis=1)
        if np.max(np.abs(V_new - V)) < tol:
            V = V_new
            break
        V = V_new
    pi = Q.argmax(axis=1)
    return V, Q, pi


def bellman_residual(mdp, Q):
    """Reziduul ecuatiei Bellman de optimalitate pentru un tabel Q dat:
    max_{s,a} | Q(s,a) - sum_s' P[s,a,s'] (R[s,a,s'] + gamma max_a' Q(s',a')) |.
    Zero (numeric mic) <=> Q satisface ecuatia de optimalitate."""
    P, R, gamma = mdp.P, mdp.R, mdp.gamma
    V = Q.max(axis=1)
    target = np.einsum("sap,sap->sa", P, R + gamma * V[None, None, :])
    return float(np.max(np.abs(Q - target)))


# ============================================================ Q-LEARNING (model-free)
def greedy_policy(Q):
    """Politica greedy fata de tabelul Q: pi(s) = argmax_a Q(s,a)."""
    return np.asarray(Q).argmax(axis=1)


def epsilon_greedy_action(Q, s, epsilon, rng):
    """Alege o actiune epsilon-greedy in starea s: cu probabilitate epsilon una
    aleatoare (explorare), altfel argmax_a Q(s,a) (exploatare). Departajare
    aleatoare la egalitate ca sa nu favorizam mereu actiunea 0."""
    nA = Q.shape[1]
    if rng.random() < epsilon:
        return int(rng.integers(nA))
    row = Q[s]
    best = np.flatnonzero(row == row.max())
    return int(rng.choice(best))


def q_learning(mdp, n_episodes=5000, max_steps=40, alpha=1.0, gamma=None,
               epsilon=0.3, seed=0, alpha_decay=0.7, return_history=False):
    """Q-learning tabular, model-free, epsilon-greedy.

    Invata DOAR din tranzitii esantionate (s, a, r, s') via mdp.step -- nu atinge
    P sau R direct. Actualizarea pe fiecare pas (vezi teorie.md, derivare):

        Q(s,a) <- Q(s,a) + alpha_eff [ r + gamma max_a' Q(s',a') - Q(s,a) ]

    Rata de invatare:
      - alpha_decay in (0.5, 1]: rata POLINOMIALA per-pereche (s,a),
        alpha_eff = alpha / N(s,a)^alpha_decay, unde N(s,a) numara vizitele.
        Un exponent in (0.5, 1] satisface conditiile Robbins-Monro
        (sum alpha = inf, sum alpha^2 < inf), deci media incrementala CONVERGE la
        valoarea adevarata: reziduul Bellman -> 0, nu doar 'roieste' in jurul ei.
      - alpha_decay None (sau 0): pas CONSTANT alpha (util didactic ca sa se vada
        zgomotul rezidual care nu mai dispare -- vezi capcane in teorie.md).

    gamma None -> ia mdp.gamma. Daca return_history, intoarce si recompensa
    (nediscountata) cumulata pe episod, ca sa vedem invatarea progresand.

    Returneaza Q (sau (Q, rewards_per_episode))."""
    if gamma is None:
        gamma = mdp.gamma
    rng = np.random.default_rng(seed)
    Q = np.zeros((mdp.nS, mdp.nA))
    N = np.zeros((mdp.nS, mdp.nA))              # contor de vizite per (s,a)
    rewards = np.zeros(n_episodes)
    for ep in range(n_episodes):
        s = int(rng.integers(mdp.nS))          # start aleator -> acopera toate starile
        total = 0.0
        for _ in range(max_steps):
            a = epsilon_greedy_action(Q, s, epsilon, rng)
            s_next, r = mdp.step(s, a, rng)
            N[s, a] += 1.0
            if alpha_decay:
                step = alpha / (N[s, a] ** alpha_decay)
            else:
                step = alpha
            best_next = Q[s_next].max()
            td_error = r + gamma * best_next - Q[s, a]
            Q[s, a] += step * td_error
            total += r
            s = s_next
        rewards[ep] = total
    if return_history:
        return Q, rewards
    return Q


# ============================================================ EVALUARE A UNEI POLITICI
def policy_values(mdp, policy):
    """Functia de valoare EXACTA a unei politici deterministe (evaluare de politica,
    rezolvare directa a sistemului liniar Bellman): V_pi = (I - gamma P_pi)^{-1} r_pi."""
    policy = np.asarray(policy)
    nS = mdp.nS
    P_pi = mdp.P[np.arange(nS), policy]                 # (nS, nS)
    r_pi = mdp.expected_reward()[np.arange(nS), policy]  # (nS,)
    return np.linalg.solve(np.eye(nS) - mdp.gamma * P_pi, r_pi)


def average_episode_reward(mdp, policy, n_episodes=200, max_steps=40, seed=0):
    """Recompensa medie (nediscountata) pe episod a unei politici, estimata prin
    simulare. `policy` poate fi un array determinist (policy[s] -> actiune) sau un
    callable selector(s, rng) -> actiune (ex: politica aleatoare). Da o masura de
    misiune interpretabila, folosita de demo si selftest sa compare politici."""
    if callable(policy):
        select = policy
    else:
        policy = np.asarray(policy)
        select = lambda s, _rng: int(policy[s])
    rng = np.random.default_rng(seed)
    totals = np.zeros(n_episodes)
    for ep in range(n_episodes):
        s = int(rng.integers(mdp.nS))
        total = 0.0
        for _ in range(max_steps):
            a = select(s, rng)
            s, r = mdp.step(s, a, rng)
            total += r
        totals[ep] = total
    return float(totals.mean())


# ============================================================ SELFTEST
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    mdp = make_link_switch_mdp(gamma=0.9)

    # referinta optima prin programare dinamica
    V_star, Q_star, pi_star = value_iteration(mdp)
    ck("value_iteration: politica = [DDS, Zenoh, Zenoh] (asteptat)",
       list(pi_star) == [0, 1, 1])
    ck("value_iteration: reziduu Bellman ~ 0 pe Q*", bellman_residual(mdp, Q_star) < 1e-8)

    # (1) Q-learning converge la politica OPTIMA a MDP-ului cunoscut
    Q, rewards = q_learning(mdp, n_episodes=5000, max_steps=40, alpha=1.0,
                            epsilon=0.3, seed=0, alpha_decay=0.7, return_history=True)
    ck("q_learning: istoric de recompense pe episod returnat (return_history)",
       rewards.shape == (5000,))
    pi_learned = greedy_policy(Q)
    ck("q_learning: politica invatata == politica optima (value_iteration)",
       list(pi_learned) == list(pi_star))

    # (2) la convergenta, valorile satisfac ecuatia Bellman (reziduu mic pe Q invatat).
    #     Rata polinomiala 1/n^0.7 (Robbins-Monro) face reziduul sa tinda la 0.
    res = bellman_residual(mdp, Q)
    ck("q_learning: reziduu Bellman mic pe Q invatat (< 0.6)", res < 0.6)
    # si valorile greedy ~ V* (toleranta laxa, e estimare stocastica)
    V_learned = Q.max(axis=1)
    ck("q_learning: V invatat ~ V* (eroare relativa < 5%)",
       np.max(np.abs(V_learned - V_star) / np.abs(V_star)) < 0.05)

    # (3) recompensa cumulata pe episod CRESTE cu antrenarea. MDP-ul de comutare e
    #     usor (politica optima e gasita repede), deci semnalul curat e: politica
    #     greedy INVATATA bate clar o politica ALEATOARE (a nu invata nimic).
    rand_policy = lambda s, rng: int(rng.integers(mdp.nA))
    r_random = average_episode_reward(mdp, rand_policy, n_episodes=300, max_steps=40, seed=7)
    r_learned = average_episode_reward(mdp, pi_learned, n_episodes=300, max_steps=40, seed=7)
    ck("q_learning: recompensa politicii invatate > a unei politici aleatoare",
       r_learned > r_random + 10.0)

    # (4) epsilon-greedy cu epsilon > 0 viziteaza TOATE actiunile in FIECARE stare
    rng = np.random.default_rng(1)
    Qfix = np.array([[5.0, 1.0], [1.0, 5.0], [2.0, 3.0]])  # actiuni clar dominante
    seen = {s: set() for s in range(3)}
    for _ in range(2000):
        for s in range(3):
            seen[s].add(epsilon_greedy_action(Qfix, s, epsilon=0.3, rng=rng))
    ck("epsilon-greedy: cu epsilon>0 viziteaza ambele actiuni in fiecare stare",
       all(seen[s] == {0, 1} for s in range(3)))
    # iar cu epsilon = 0 ramane strict greedy (doar argmax)
    rng2 = np.random.default_rng(2)
    greedy_only = set(epsilon_greedy_action(Qfix, 0, epsilon=0.0, rng=rng2) for _ in range(50))
    ck("epsilon-greedy: cu epsilon=0 ia mereu argmax (exploatare pura)",
       greedy_only == {0})

    # (5) evaluarea exacta de politica == V din value_iteration pentru pi*
    V_pi_star = policy_values(mdp, pi_star)
    ck("policy_values: V_pi* == V* (programare dinamica)", np.allclose(V_pi_star, V_star, atol=1e-6))
    # iar pi* are valoare cel putin la fel de buna ca orice politica statica
    V_dds = policy_values(mdp, np.zeros(mdp.nS, dtype=int))
    V_zen = policy_values(mdp, np.ones(mdp.nS, dtype=int))
    ck("policy_values: pi* domina politicile statice (mereu-DDS / mereu-Zenoh)",
       np.all(V_pi_star >= V_dds - 1e-9) and np.all(V_pi_star >= V_zen - 1e-9))

    print("\nTOATE VERIFICARILE qlearning_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
