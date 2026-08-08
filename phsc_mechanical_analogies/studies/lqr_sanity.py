#!/usr/bin/env python3
"""
lqr_sanity.py
Verificare a implementarii LQR inainte de a trage concluzii despre arhitectura.

Daca LQR nu stabilizeaza nici FARA latenta, atunci bancul de test e gresit,
nu arhitectura. Testam in trepte:
  1. LQR fara latenta deloc
  2. LQR cu latenta, fara compensare
  3. LQR cu predictie care presupune u=0 pe fereastra (varianta naiva)
  4. LQR cu predictie care foloseste comenzile IN ZBOR (Smith corect)
"""

import numpy as np
import _context  # noqa: F401  -- pachetul importabil si din sursa
from phsc_mechanical_analogies.cartpole_model import CartPoleModel, DelayedCartPole

DT = 0.001
T_END = 6.0
THETA0 = 0.10
FAIL = np.radians(60)

model = CartPoleModel()
K = model.lqr_gain()


def run(name, tau_fn, predictor, period=0.01):
    plant = DelayedCartPole()
    x = np.array([0.0, 0.0, THETA0, 0.0])
    t, u_cmd, t_next = 0.0, 0.0, 0.0
    sent = []          # (t_emis, u) -- comenzile deja trimise pe canal
    ths = []
    fell = None
    while t < T_END:
        if t >= t_next:
            u_cmd = predictor(x.copy(), t, tau_fn(t), sent)
            u_cmd = float(np.clip(u_cmd, -100.0, 100.0))
            sent.append((t, u_cmd))
            t_next = t + period
        plant.control_history.append((t, u_cmd))
        u_app = plant.get_delayed_control(t, tau_fn(t)) if tau_fn(t) > 0 else u_cmd
        x = plant.dynamics_rk4(x, u_app, DT)
        ths.append(x[2])
        if fell is None and abs(x[2]) > FAIL:
            fell = t
        t += DT
    ths = np.array(ths)
    ok = fell is None and abs(ths[-1]) < np.radians(5)
    print(f"  {name:<52} |theta|max={np.degrees(np.abs(ths).max()):8.2f}d  "
          f"{'STABIL' if ok else ('CAZUT la %.2fs' % fell if fell else 'NESTABILIZAT')}")
    return ok


def p_direct(x, t, tau, sent):
    return -(K @ x)[0]


def p_naiv(x, t, tau, sent):
    """Predictie presupunand u=0 pe fereastra de latenta (ce am testat initial)."""
    xp = x.copy()
    n = 8
    for _ in range(n):
        xp = model.dynamics_rk4(xp, 0.0, tau / n)
    return -(K @ xp)[0]


def p_smith(x, t, tau, sent):
    """
    Predictie CORECTA: propaga starea masurata inainte cu tau folosind
    comenzile deja trimise si inca neajunse la planta (in zbor).
    Asta e ce lipsea: control_buffer era scris si niciodata folosit.
    """
    xp = x.copy()
    n = 8
    dtp = tau / n
    for i in range(n):
        t_i = t + i * dtp
        # ce comanda va actiona pe planta la momentul t_i (emisa la t_i - tau)
        u_i = 0.0
        target = t_i - tau
        for (ts, us) in reversed(sent):
            if ts <= target:
                u_i = us
                break
        xp = model.dynamics_rk4(xp, u_i, dtp)
    return -(K @ xp)[0]


print("=" * 88)
print("SANITY LQR -- fiecare treapta izoleaza o singura cauza")
print("=" * 88)
run("1. LQR, FARA latenta (100 Hz)", lambda t: 0.0, p_direct)
run("2. LQR, latenta 80+/-20 ms, fara compensare", lambda t: 0.08 + 0.02*np.sin(2*t), p_direct)
run("3. LQR + predictie naiva (u=0 pe fereastra)", lambda t: 0.08 + 0.02*np.sin(2*t), p_naiv)
run("4. LQR + predictie Smith (comenzi in zbor)", lambda t: 0.08 + 0.02*np.sin(2*t), p_smith)
print()
print("Prag de latenta pentru LQR + predictie Smith (100 Hz):")
for tau0 in (0.02, 0.04, 0.06, 0.08, 0.10, 0.15, 0.20):
    run(f"   tau constant = {tau0*1000:.0f} ms", lambda t, a=tau0: a, p_smith)
print("=" * 88)
