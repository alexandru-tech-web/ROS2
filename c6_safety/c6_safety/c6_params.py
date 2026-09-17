#!/usr/bin/env python3
"""c6_params.py -- toti parametrii experimentului C6, intr-un singur loc.

Fiecare camp marcat [de fixat] in caiet e o PROPUNERE, nu o valoare stabilita.
Se schimba aici, nu in cod.
"""
from dataclasses import dataclass, field


@dataclass
class Params:
    # --- vehicul (caiet v0.1 sec. 2) ---
    dt: float = 0.05          # s; propus in caiet v0.1 sec. 2 (20 Hz); de fixat in N-C6
    a_max: float = 1.0        # m/s^2; propus in caiet v0.1 sec. 2; de fixat in N-C6
    tau_act: float = 0.0      # s; ERATA v0.2, 17.09: plantul e clamp pur, lag = lucru
                              # viitor; 0.2 se foloseste DOAR de testul de robustete (g)
    v_max: float = 1.0        # m/s; propus in caiet v0.1 sec. 2; de fixat in N-C6
    omega_max: float = 1.5    # rad/s; propus in caiet v0.1 sec. 2; de fixat in N-C6
    l: float = 0.2            # m, punctul de control; propus in caiet v0.1 sec. 2; de fixat in N-C6

    # --- scenariu (caiet v0.1 sec. 3) ---
    start: tuple = (0.0, 0.0, 0.0)   # propus in caiet v0.1 sec. 3; de fixat in N-C6
    goal: tuple = (10.0, 0.0)        # propus in caiet v0.1 sec. 3; de fixat in N-C6
    obst: tuple = (5.0, 0.5)         # propus in caiet v0.1 sec. 3; de fixat in N-C6
    r: float = 1.0                   # m, raza de siguranta; propus in caiet v0.1 sec. 3; de fixat in N-C6
    goal_tol: float = 0.3            # m; propus in caiet v0.1 sec. 8; de fixat in N-C6
    T_max: float = 60.0              # s; propus in caiet v0.1 sec. 8; de fixat in N-C6

    # --- canal si operator ---
    T_hold: float = 0.5       # s, hold-last-command; propus in caiet v0.1 sec. 4; de fixat in N-C6
    k_v: float = 0.5          # castig P pe viteza; propus in caiet v0.1 sec. 3; de fixat in N-C6
    k_w: float = 2.0          # castig P pe orientare; propus in caiet v0.1 sec. 3; de fixat in N-C6
    seed: int = 1             # propus in caiet v0.1 sec. 7; de fixat in N-C6
