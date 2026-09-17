#!/usr/bin/env python3
"""operator_core.py -- operatorul uman, simulat.

v0.1: P spre tinta, NU vede obstacolul. Rezultatul din S2: cu tinta drept
inainte, operatorul cere (v_max, 0) la nesfarsit, filtrul franeaza, si roverul
sta la h = 0 pentru totdeauna -- sigur si inutil.

v0.2 (17.09, react=True): un operator care REACTIONEAZA, cu intarziere umana.
La t = T_react vireaza 45 de grade fata de directia spre tinta, spre partea cu
h mai mare, tine virajul DURATA_REACT secunde, apoi revine la P. Nu e evitare
de obstacol -- e un om care da din volan o data, tarziu, si apoi isi vede de
drum. Filtrul ramane responsabil de siguranta.

INTERPRETARE (de confirmat de Alexandru): "T_react = 1.0 s" e citit ca momentul
absolut al reactiei fata de startul episodului, nu ca intarziere fata de o
detectie -- specificatia nu da un prag de detectie, si nu inventam unul.
"""
import math

T_REACT = 1.0        # s; propus 17.09; de fixat in N-C6
UNGHI_REACT = math.radians(45.0)
DURATA_REACT = 2.0   # s


def _eroare_unghi(tinta, theta):
    return math.atan2(math.sin(tinta - theta), math.cos(tinta - theta))


def _partea_cu_h_mai_mare(state, params, dir_goal):
    """+1 = stanga (unghi +45), -1 = dreapta. Se evalueaza h la p_c dupa un pas
    ipotetic pe fiecare parte; castiga partea care lasa h mai mare."""
    ox, oy = params.obst
    best = None
    for semn in (+1, -1):
        th = dir_goal + semn * UNGHI_REACT
        s = params.v_max * params.dt
        cx = state.x + s * math.cos(th) + params.l * math.cos(th)
        cy = state.y + s * math.sin(th) + params.l * math.sin(th)
        h = math.hypot(cx - ox, cy - oy)
        if best is None or h > best[0]:
            best = (h, semn)
    return best[1]


def op_cmd(state, params, t=None, react=False):
    """(v_op, omega_op). react=True cere si timpul t."""
    gx, gy = params.goal
    dx, dy = gx - state.x, gy - state.y
    dist = math.hypot(dx, dy)
    dir_goal = math.atan2(dy, dx)

    tinta = dir_goal
    if react and t is not None and T_REACT <= t < T_REACT + DURATA_REACT:
        tinta = dir_goal + _partea_cu_h_mai_mare(state, params, dir_goal) * UNGHI_REACT

    err = _eroare_unghi(tinta, state.theta)
    v = max(0.0, min(params.v_max, params.k_v * dist))
    w = max(-params.omega_max, min(params.omega_max, params.k_w * err))
    return v, w
