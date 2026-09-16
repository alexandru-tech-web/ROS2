#!/usr/bin/env python3
"""operator_core.py -- operatorul uman, simulat. NU vede obstacolul.

Asta e intentia experimentului: daca operatorul l-ar ocoli, filtrul nu ar avea ce
demonstra. Comanda merge drept spre tinta; evitarea e treaba filtrului (S2).
"""
import math


def op_cmd(state, params):
    """(v_op, omega_op): proportional spre goal, saturat la v_max / omega_max."""
    gx, gy = params.goal
    dx, dy = gx - state.x, gy - state.y
    dist = math.hypot(dx, dy)
    err = math.atan2(math.sin(math.atan2(dy, dx) - state.theta),
                     math.cos(math.atan2(dy, dx) - state.theta))
    v = max(0.0, min(params.v_max, params.k_v * dist))
    w = max(-params.omega_max, min(params.omega_max, params.k_w * err))
    return v, w
