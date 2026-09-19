#!/usr/bin/env python3
"""c6_params.py -- toti parametrii experimentului C6, intr-un singur loc.

Toate valorile sunt SEMNATE (caiet C6 v0.2 + ERATE; ultimele etichete scoase la K4.1, 19.09.2026).
Se schimba aici, nu in cod.
"""
from dataclasses import dataclass, field


@dataclass
class Params:
    # --- vehicul (caiet v0.1 sec. 2) ---
    dt: float = 0.05          # s; propus in caiet v0.1 sec. 2 (20 Hz); SEMNAT 19.09 (K4.1)
    a_max: float = 1.0        # m/s^2; propus in caiet v0.1 sec. 2; SEMNAT 19.09 (K4.1)
    tau_act: float = 0.0      # s; ERATA v0.2, 17.09: plantul e clamp pur, lag = lucru
                              # viitor; 0.2 se foloseste DOAR de testul de robustete (g)
    v_max: float = 1.0        # m/s; propus in caiet v0.1 sec. 2; SEMNAT 19.09 (K4.1)
    omega_max: float = 1.5    # rad/s; propus in caiet v0.1 sec. 2; SEMNAT 19.09 (K4.1)
    l: float = 0.2            # m, punctul de control; propus in caiet v0.1 sec. 2; SEMNAT 19.09 (K4.1)

    # --- scenariu (caiet v0.1 sec. 3) ---
    start: tuple = (0.0, 0.0, 0.0)   # propus in caiet v0.1 sec. 3; SEMNAT 19.09 (K4.1)
    goal: tuple = (10.0, 0.0)        # propus in caiet v0.1 sec. 3; SEMNAT 19.09 (K4.1)
    obst: tuple = (5.0, 0.5)         # propus in caiet v0.1 sec. 3; SEMNAT 19.09 (K4.1)
    r: float = 1.0                   # m, raza de siguranta; propus in caiet v0.1 sec. 3; SEMNAT 19.09 (K4.1)
    goal_tol: float = 0.3            # m; propus in caiet v0.1 sec. 8; SEMNAT 19.09 (K4.1)
    T_max: float = 60.0              # s; propus in caiet v0.1 sec. 8; SEMNAT 19.09 (K4.1)

    # --- canal si operator ---
    T_hold: float = 0.5       # s, hold-last-command; propus in caiet v0.1 sec. 4; SEMNAT 19.09 (K4.1)
    k_v: float = 0.5          # castig P pe viteza; propus in caiet v0.1 sec. 3; SEMNAT 19.09 (K4.1)
    k_w: float = 2.0          # castig P pe orientare; propus in caiet v0.1 sec. 3; SEMNAT 19.09 (K4.1)
    seed: int = 1             # propus in caiet v0.1 sec. 7; SEMNAT 19.09 (K4.1)

    # --- ERATA v0.2 (17.09): marjele bratelor S2b ---
    # A1: marja_extra = 0 (CBF ne-constient de retea)
    # A2: marja_extra = v_o_max * A_haz          (contributia, Lema 1)
    # A3: r_eff = r + d_fr(v_max) + v_o_max * AoI_max  (cel mai rau caz, fix)
    v_o_max: float = 0.5      # m/s; DECIZIE v0.2 (nucleu; sweep 1.0, 1.5)
    f_haz: float = 5.0        # Hz;  DECIZIE v0.2 (nucleu; sweep 2)
    # ERATA 2 v0.2: pericolul porneste din -v_o*t_cross ca sa traverseze y=0 cand roverul
    # ajunge la x=6 (S2b: pornit din -2 trecea la t=4 s, roverul ajungea la 7.7 s -> A0 trivial sigur)
    t_cross: float = 7.5      # s; ERATA 2, SEMNAT 19.09 (K4.1)
    hazard_x: float = 6.0
    hazard_end_y: float = 2.0           # se opreste la (6, +2)
    AoI_max: float = 1.0      # s; ERATA 2: plafonul marjei A2, SEMNAT 19.09 (K4.1); peste el -> stare sigura (n_ws)
    AoI_max_A3: float = 0.5   # s; = T_hold, varsta presupusa de A3 (ERATA v0.2)
    scenariu: str = "traversare"   # ERATA 3: "traversare" | "urmarire"

    @property
    def hazard_start(self):
        return (self.hazard_x, -self.v_o_max * self.t_cross)
