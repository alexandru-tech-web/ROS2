#!/usr/bin/env python3
"""
benchmark_mpc.py
Masoara performanta MPC neliniar (SLSQP) si o compara cu alternativele
real-time. Decide arhitectura: nonlinear MPC offline vs linear MPC vs LQR.

Nota: fara sys.path hardcodat -- se ruleaza din ~/phsc_sim, unde stau copiile.
"""

import time
import numpy as np

import _context  # noqa: F401  -- pachetul importabil si din sursa
from phsc_mechanical_analogies.cartpole_model import CartPoleModel
from phsc_mechanical_analogies.mpc_controller import MPCParams, MPCController

model = CartPoleModel()
x0 = np.array([0.0, 0.0, 0.1, 0.0])
x_ref = np.zeros(4)


def bench(fn, n=10, warmup=1):
    for _ in range(warmup):
        fn()
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return np.array(ts)


print("=" * 62)
print("A. MPC NELINIAR (SLSQP), asa cum e configurat in mpc_tuning.yaml")
print("=" * 62)
for N in (20, 15, 10, 7, 5):
    params = MPCParams(N=N, dt=0.05, u_max=100.0,
                       Q=np.diag([10., 1., 100., 1.]),
                       R=np.array([[0.01]]),
                       P=np.diag([50., 5., 500., 5.]))
    mpc = MPCController(model, params)
    t = bench(lambda: mpc.solve(x0, x_ref), n=10)
    ok = "OK" if np.median(t) < 0.05 else "LENT"
    print(f"  N={N:2d}: mediana={np.median(t)*1000:7.1f} ms  "
          f"min={t.min()*1000:6.1f}  max={t.max()*1000:7.1f}  "
          f"-> {1.0/np.median(t):5.1f} Hz  [{ok}]")

print()
print("=" * 62)
print("B. ALTERNATIVE REAL-TIME (aceeasi masina, acelasi x0)")
print("=" * 62)

# B1. LQR: castig precalculat, control = o singura inmultire matrice-vector
K = model.lqr_gain()
t = bench(lambda: -(K @ x0)[0], n=1000, warmup=10)
print(f"  LQR (K precalculat):        mediana={np.median(t)*1e6:8.2f} us "
      f"-> {1.0/np.median(t)/1000:.0f} kHz")

# B2. LQR + predictie neliniara RK4 pe fereastra de delay (propunerea Kimi)
def lqr_pred():
    xp = x0.copy()
    dt_pred = 0.08 / 20
    for _ in range(20):
        xp = model.dynamics_rk4(xp, 0.0, dt_pred)
    return -(K @ xp)[0]

t = bench(lqr_pred, n=1000, warmup=10)
print(f"  LQR + predictie RK4 (20 pasi): mediana={np.median(t)*1e6:8.2f} us "
      f"-> {1.0/np.median(t):.0f} Hz")

# B3. acelasi lucru cu 4 pasi RK4 (suficient pentru tau=80 ms)
def lqr_pred4():
    xp = x0.copy()
    for _ in range(4):
        xp = model.dynamics_rk4(xp, 0.0, 0.02)
    return -(K @ xp)[0]

t = bench(lqr_pred4, n=1000, warmup=10)
print(f"  LQR + predictie RK4 (4 pasi):  mediana={np.median(t)*1e6:8.2f} us "
      f"-> {1.0/np.median(t):.0f} Hz")

print()
print("=" * 62)
print("C. CONCLUZIE")
print("=" * 62)
params = MPCParams(N=20, dt=0.05, u_max=100.0,
                   Q=np.diag([10., 1., 100., 1.]),
                   R=np.array([[0.01]]),
                   P=np.diag([50., 5., 500., 5.]))
mpc = MPCController(model, params)
t20 = bench(lambda: mpc.solve(x0, x_ref), n=10)
med = np.median(t20)
print(f"  MPC neliniar N=20 : {med*1000:.0f} ms  -> {1.0/med:.1f} Hz")
print(f"  Necesar pentru 20 Hz: < 50 ms")
print(f"  Verdict: {'OK' if med < 0.05 else 'NESUSTENABIL in timp real'}")
print(f"  Raport fata de bugetul de 50 ms: {med/0.05:.0f}x peste")
# Polul instabil determina rata minima de esantionare
A, _ = model.linearized_matrices()
pol = max(np.linalg.eigvals(A).real)
print(f"  Pol instabil in bucla deschisa: {pol:.2f} rad/s "
      f"(constanta de timp {1/pol*1000:.0f} ms)")
print(f"  Regula practica (>=10 esantioane / constanta de timp): "
      f"necesar >= {10*pol/(2*np.pi):.0f} Hz")
print("=" * 62)
