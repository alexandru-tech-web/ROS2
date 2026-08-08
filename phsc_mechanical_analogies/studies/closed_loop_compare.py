#!/usr/bin/env python3
"""
closed_loop_compare.py
Experimentul care decide arhitectura runda 2.

Intrebarea: NMPC offline + LQR real-time, sau NMPC cu N mic in timp real?

Benchmark-ul pur de viteza nu raspunde, pentru ca un controller lent dar
"mai destept" ar putea totusi castiga. Aici simulam bucla INCHISA cu
constrangerea de timp real respectata: fiecare controller isi actualizeaza
comanda doar la intervalul pe care si-l poate permite EFECTIV (timpul lui
de solve masurat), nu la cel nominal. Intre actualizari, comanda e tinuta
(zero-order hold), exact ca in nodul ROS.

Planta: cart-pole neliniar, integrat la 1 ms.
Canal: latenta variabila tau(t) = 0.08 + 0.02*sin(2t) pe calea de comanda.
"""

import time
import numpy as np

import _context  # noqa: F401  -- pachetul importabil si din sursa
from phsc_mechanical_analogies.cartpole_model import CartPoleModel, DelayedCartPole
from phsc_mechanical_analogies.mpc_controller import MPCParams, DelayCompensatedMPC

DT_SIM = 0.001
T_END = 6.0
THETA0 = 0.10
TAU = lambda t: 0.08 + 0.02 * np.sin(2.0 * t)
THETA_FAIL = np.radians(60.0)   # peste asta consideram ca pendulul a cazut


def simulate(name, control_fn, period, model_params=None):
    """
    control_fn(x_meas, t) -> u
    period: intervalul REAL intre actualizari de comanda [s]
    """
    plant = DelayedCartPole()
    x = np.array([0.0, 0.0, THETA0, 0.0])
    t = 0.0
    u_cmd = 0.0
    t_next = 0.0

    ths, us, ts = [], [], []
    fell_at = None
    n_updates = 0

    while t < T_END:
        if t >= t_next:
            u_cmd = control_fn(x.copy(), t)
            n_updates += 1
            t_next = t + period

        # canalul cu latenta: comanda emisa acum ajunge la planta cu tau(t)
        plant.control_history.append((t, u_cmd))
        u_applied = plant.get_delayed_control(t, TAU(t))
        x = plant.dynamics_rk4(x, u_applied, DT_SIM)

        ths.append(x[2]); us.append(u_cmd); ts.append(t)
        if fell_at is None and abs(x[2]) > THETA_FAIL:
            fell_at = t
        t += DT_SIM

    ths = np.array(ths); us = np.array(us)
    stabil = fell_at is None and abs(ths[-1]) < np.radians(5)
    return {
        'nume': name,
        'perioada_ms': period * 1000,
        'rata_hz': 1.0 / period,
        'actualizari': n_updates,
        'theta_max_deg': np.degrees(np.abs(ths).max()),
        'theta_rms_deg': np.degrees(np.sqrt((ths ** 2).mean())),
        'theta_final_deg': np.degrees(ths[-1]),
        'efort_rms_N': np.sqrt((us ** 2).mean()),
        'cazut_la_s': fell_at,
        'stabil': stabil,
    }


model = CartPoleModel()
K = model.lqr_gain()
x_ref = np.zeros(4)
rezultate = []

# --- 1. NMPC N=20, la rata pe care si-o permite efectiv (~1.9 Hz) ---
for N in (20, 10, 7):
    params = MPCParams(N=N, dt=0.05, u_max=100.0,
                       Q=np.diag([10., 1., 100., 1.]),
                       R=np.array([[0.01]]),
                       P=np.diag([50., 5., 500., 5.]))
    mpc = DelayCompensatedMPC(model, params)
    # masuram timpul real de solve pentru acest N
    t0 = time.perf_counter()
    mpc.step(np.array([0., 0., THETA0, 0.]), x_ref, TAU, 0.0)
    t_solve = time.perf_counter() - t0
    mpc.reset()
    period = max(params.dt, t_solve)

    def mk(mpc_local):
        def f(x, t):
            u, _, ok = mpc_local.step(x, x_ref, TAU, t)
            if not ok or not np.isfinite(u):
                u = float(-(K @ x)[0])
            return float(np.clip(u, -100.0, 100.0))
        return f

    print(f"  ... rulez NMPC N={N} (solve {t_solve*1000:.0f} ms, "
          f"perioada reala {period*1000:.0f} ms)", flush=True)
    rezultate.append(simulate(f"NMPC N={N} (real-time)", mk(mpc), period))

# --- 2. LQR + predictie neliniara RK4 pe fereastra de delay, 100 Hz ---
_sent = []

def lqr_naiv(x, t):
    xp = x.copy(); tau = TAU(t); n = 8
    for _ in range(n):
        xp = model.dynamics_rk4(xp, 0.0, tau / n)
    return float(np.clip(-(K @ xp)[0], -100.0, 100.0))

def lqr_smith(x, t):
    tau = TAU(t); n = 8; dtp = tau / n
    xp = x.copy()
    for i in range(n):
        target = t + i * dtp - tau
        u_i = 0.0
        for (ts, us) in reversed(_sent):
            if ts <= target:
                u_i = us; break
        xp = model.dynamics_rk4(xp, u_i, dtp)
    u = float(np.clip(-(K @ xp)[0], -100.0, 100.0))
    _sent.append((t, u))
    if len(_sent) > 500: del _sent[:-500]
    return u

print("  ... rulez LQR + predictie NAIVA (u=0) 100 Hz", flush=True)
rezultate.append(simulate("LQR + predictie naiva", lqr_naiv, 0.01))
_sent.clear()
print("  ... rulez LQR + predictie SMITH (in zbor) 100 Hz", flush=True)
rezultate.append(simulate("LQR + predictie Smith", lqr_smith, 0.01))

# --- 3. LQR simplu, fara compensare de delay, 100 Hz (baseline) ---
def lqr_plain(x, t):
    return float(np.clip(-(K @ x)[0], -100.0, 100.0))

print("  ... rulez LQR simplu, fara compensare (100 Hz)", flush=True)
rezultate.append(simulate("LQR fara compensare", lqr_plain, 0.01))

# --- raport ---
print()
print("=" * 100)
print(f"BUCLA INCHISA: cart-pole, theta0={np.degrees(THETA0):.0f} grade, "
      f"tau(t)=80+/-20 ms, {T_END:.0f} s de simulare")
print("=" * 100)
hdr = (f"{'controller':<26} {'rata':>9} {'upd':>5} "
       f"{'|theta|max':>11} {'theta rms':>10} {'theta fin':>10} "
       f"{'u rms':>8}  verdict")
print(hdr)
print("-" * 100)
for r in rezultate:
    verdict = "STABIL" if r['stabil'] else (
        f"CAZUT la {r['cazut_la_s']:.2f}s" if r['cazut_la_s'] else "NESTABILIZAT")
    print(f"{r['nume']:<26} {r['rata_hz']:>7.1f}Hz {r['actualizari']:>5} "
          f"{r['theta_max_deg']:>10.2f}d {r['theta_rms_deg']:>9.2f}d "
          f"{r['theta_final_deg']:>9.2f}d {r['efort_rms_N']:>7.2f}N  {verdict}")
print("=" * 100)
