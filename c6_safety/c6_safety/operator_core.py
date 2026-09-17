#!/usr/bin/env python3
"""operator_core.py -- operatorul uman, simulat. ORB la pericol.

ERATA v0.2 (17.09): react=False e SCENARIUL DE BAZA -- filtrul decide, operatorul
nu vede nimic si cere P spre tinta la nesfarsit. Pretul sigurantei cu un operator
orb (B, T_G) e chiar motivatia C5, deci NU se ascunde.

react=True e un SUB-BLOC (factor F7): un om care observa ca s-a blocat si da din
volan. Declansare pe BLOCAJ, nu la un timp absolut:
    v < 0.05 m/s si v_op > 0.2 m/s, CONTINUU cel putin T_react = 1.0 s
apoi viraj 45 grade spre partea cu h mai mare, timp de DURATA_REACT = 2 s, apoi
P; re-armare dupa T_REARM = 1 s (poate reactiona din nou daca se blocheaza iar).

Operatorul are STARE (cronometre), deci e o clasa. op_cmd() ramane pentru
compatibilitate si e echivalent cu Operator(react=False).
"""
import math

T_REACT = 1.0        # s, blocaj continuu inainte de reactie; ERATA v0.2
UNGHI_REACT = math.radians(45.0)
DURATA_REACT = 2.0   # s
T_REARM = 1.0        # s
V_BLOCAT = 0.05      # m/s, caiet sec. 8
V_OP_ACTIV = 0.2     # m/s, caiet sec. 8


def _eroare_unghi(tinta, theta):
    return math.atan2(math.sin(tinta - theta), math.cos(tinta - theta))


def _partea_cu_h_mai_mare(state, params, dir_goal):
    """+1 = stanga, -1 = dreapta: partea care lasa h mai mare dupa un pas ipotetic."""
    ox, oy = params.obst
    best = None
    for semn in (+1, -1):
        th = dir_goal + semn * UNGHI_REACT
        s = params.v_max * params.dt
        cx = state.x + (s + params.l) * math.cos(th)
        cy = state.y + (s + params.l) * math.sin(th)
        h = math.hypot(cx - ox, cy - oy)
        if best is None or h > best[0]:
            best = (h, semn)
    return best[1]


def _p_spre_goal(state, params):
    gx, gy = params.goal
    dx, dy = gx - state.x, gy - state.y
    return math.hypot(dx, dy), math.atan2(dy, dx)


class Operator(object):
    def __init__(self, params, react=False):
        self.p = params
        self.react = react
        self.t_blocaj = None      # de cand e blocat continuu
        self.t_viraj = None       # de cand vireaza
        self.semn = 0
        self.t_rearm = -1.0       # cand poate reactiona din nou
        self.n_reactii = 0

    def cmd(self, state, t):
        p = self.p
        dist, dir_goal = _p_spre_goal(state, p)
        v = max(0.0, min(p.v_max, p.k_v * dist))
        tinta = dir_goal

        if self.react:
            # in viraj?
            if self.t_viraj is not None:
                if t - self.t_viraj < DURATA_REACT:
                    tinta = dir_goal + self.semn * UNGHI_REACT
                else:
                    self.t_viraj = None
                    self.t_rearm = t + T_REARM
            else:
                blocat = (state.v < V_BLOCAT and v > V_OP_ACTIV and t >= self.t_rearm)
                if blocat:
                    if self.t_blocaj is None:
                        self.t_blocaj = t
                    elif t - self.t_blocaj >= T_REACT:
                        self.semn = _partea_cu_h_mai_mare(state, p, dir_goal)
                        self.t_viraj = t
                        self.t_blocaj = None
                        self.n_reactii += 1
                        tinta = dir_goal + self.semn * UNGHI_REACT
                else:
                    self.t_blocaj = None

        err = _eroare_unghi(tinta, state.theta)
        w = max(-p.omega_max, min(p.omega_max, p.k_w * err))
        return v, w


def op_cmd(state, params, t=None, react=False):
    """Compatibilitate: fara stare, deci DOAR react=False are sens aici."""
    return Operator(params, react=False).cmd(state, t or 0.0)
