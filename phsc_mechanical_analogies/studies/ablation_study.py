#!/usr/bin/env python3
"""
ablation_study.py
Studiu de ablatie pentru compensarea latentei, cu LQR pe cart-pole.

Trei conditii:
  1. 'none'  -- fara compensare: LQR direct pe starea masurata
  2. 'naive' -- predictie care presupune u=0 pe fereastra de latenta
  3. 'smith' -- predictie cu comenzile REALE din buffer (in zbor pe canal)

Ipoteza de verificat: #2 este MAI REA decat #1, desi #2 'compenseaza'.

Toti trei ruleaza la aceeasi rata (100 Hz) si pe aceeasi planta, deci
singura variabila este ce presupune predictorul despre comanda.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import _context  # noqa: F401  -- pachetul importabil si din sursa
from phsc_mechanical_analogies.cartpole_model import CartPoleModel, DelayedCartPole

DT = 0.01          # perioada controllerului [s] (100 Hz)
DT_SIM = 0.001     # pas de integrare al plantei [s]
T_END = 5.0
X0 = np.array([0.0, 0.0, 0.10, 0.0])
FAIL = np.pi / 2   # 90 grade = cazut
N_PRED = 20

model = CartPoleModel()
K = model.lqr_gain()


def run(mode, tau_func, T=T_END):
    """
    Planta e integrata la DT_SIM; controllerul se actualizeaza la DT.
    Canalul aplica u(t - tau(t)) prin acelasi mecanism pentru toate modurile.
    """
    plant = DelayedCartPole()
    x = X0.copy()
    t = 0.0
    u_cmd = 0.0
    t_next = 0.0
    buf = []                      # (t, u) comenzi emise
    ts, ths, us = [], [], []
    fell = None

    while t < T:
        if t >= t_next:
            tau = tau_func(t)
            if mode == 'none':
                x_hat = x
            elif mode == 'naive':
                # presupune u=0 pe toata fereastra
                x_hat = model.predict_state_delay(x, 0.0, tau, N_PRED)
            elif mode == 'smith':
                # foloseste comenzile reale din buffer
                x_hat = model.predict_state_smith(x, tau, buf, t, N_PRED)
            else:
                raise ValueError(mode)

            u_cmd = float(np.clip(-(K @ x_hat)[0], -100.0, 100.0))
            buf.append((t, u_cmd))
            if len(buf) > 2000:
                del buf[:-2000]
            t_next = t + DT

        plant.control_history.append((t, u_cmd))
        u_app = plant.get_delayed_control(t, tau_func(t))
        x = plant.dynamics_rk4(x, u_app, DT_SIM)

        ts.append(t); ths.append(x[2]); us.append(u_cmd)
        if fell is None and abs(x[2]) > FAIL:
            fell = t
        t += DT_SIM

    ths = np.array(ths); us = np.array(us)
    stabil = fell is None and abs(ths[-1]) < np.radians(5)
    return {
        'ts': np.array(ts), 'ths': ths, 'us': us,
        'fell': fell, 'stabil': stabil,
        'th_max': np.degrees(np.abs(ths).max()),
        'th_rms': np.degrees(np.sqrt((ths ** 2).mean())),
        'u_rms': float(np.sqrt((us ** 2).mean())),
    }


# ---------------------------------------------------------------- ablatie
TAU_ABL = 0.10
print("=" * 78)
print(f"ABLATIE -- LQR pe cart-pole, tau constant = {TAU_ABL*1000:.0f} ms, "
      f"controller la {1/DT:.0f} Hz")
print("=" * 78)
print(f"{'conditie':<34} {'|theta|max':>11} {'theta rms':>10} "
      f"{'u rms':>8}  verdict")
print("-" * 78)

etichete = {
    'none':  '1. Fara compensare',
    'naive': '2. Predictie naiva (u=0)',
    'smith': '3. Predictie Smith (buffer)',
}
rez = {}
for mode in ('none', 'naive', 'smith'):
    r = run(mode, lambda t: TAU_ABL)
    rez[mode] = r
    v = "STABIL" if r['stabil'] else (
        f"CAZUT la {r['fell']:.2f}s" if r['fell'] else "NESTABILIZAT")
    print(f"{etichete[mode]:<34} {r['th_max']:>10.2f}d {r['th_rms']:>9.2f}d "
          f"{r['u_rms']:>7.2f}N  {v}")
print("-" * 78)

t_none = rez['none']['fell']
t_naive = rez['naive']['fell']
if t_none is not None and t_naive is not None:
    if t_naive < t_none:
        print(f"IPOTEZA CONFIRMATA: predictia naiva cade MAI DEVREME "
              f"({t_naive:.2f}s) decat lipsa compensarii ({t_none:.2f}s) "
              f"-- cu {(t_none-t_naive)*1000:.0f} ms mai repede.")
    else:
        print(f"IPOTEZA INFIRMATA: naiv {t_naive:.2f}s vs none {t_none:.2f}s")
else:
    print(f"Nu ambele cad: none={t_none}, naive={t_naive}")
print("=" * 78)

# ------------------------------------------------------- prag de latenta
print()
print("=" * 78)
print("PRAG DE STABILITATE pe latenta (aceeasi planta, controller 100 Hz)")
print("=" * 78)
TAUS = [0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20]
print(f"{'tau [ms]':>9} | {'fara compensare':>22} | {'naiv (u=0)':>22} | "
      f"{'Smith (buffer)':>22}")
print("-" * 78)
prag = {}
for tau in TAUS:
    linie = f"{tau*1000:>9.0f} |"
    for mode in ('none', 'naive', 'smith'):
        r = run(mode, lambda t, a=tau: a)
        if r['stabil']:
            s = f"STABIL ({r['th_max']:.1f}d)"
        elif r['fell']:
            s = f"CAZUT {r['fell']:.2f}s"
        else:
            s = f"NESTAB ({r['th_max']:.0f}d)"
        prag.setdefault(mode, {})[tau] = r['stabil']
        linie += f" {s:>22} |"
    print(linie)
print("-" * 78)
for mode in ('none', 'naive', 'smith'):
    ok = [t for t in TAUS if prag[mode][t]]
    if ok:
        ultim = max(ok)
        urm = [t for t in TAUS if t > ultim]
        if urm:
            print(f"  {etichete[mode]:<32}: prag intre "
                  f"{ultim*1000:.0f} si {min(urm)*1000:.0f} ms")
        else:
            print(f"  {etichete[mode]:<32}: stabil pe tot intervalul testat")
    else:
        print(f"  {etichete[mode]:<32}: instabil chiar si la "
              f"{TAUS[0]*1000:.0f} ms")
print("=" * 78)

# ------------------------------------------------------------------ plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
culori = {'none': '#d62728', 'naive': '#ff7f0e', 'smith': '#2ca02c'}
for mode in ('none', 'naive', 'smith'):
    r = rez[mode]
    ax1.plot(r['ts'], np.degrees(r['ths']), color=culori[mode],
             label=etichete[mode], linewidth=1.8)
    ax2.plot(r['ts'], r['us'], color=culori[mode], linewidth=1.2)

ax1.axhline(90, color='k', ls='--', alpha=0.35, lw=1)
ax1.axhline(-90, color='k', ls='--', alpha=0.35, lw=1)
ax1.set_ylabel('theta [grade]')
ax1.set_ylim(-180, 180)
ax1.set_title(f'Ablatie compensare latenta -- LQR, tau = {TAU_ABL*1000:.0f} ms, '
              f'{1/DT:.0f} Hz')
ax1.legend(loc='upper right')
ax1.grid(True, alpha=0.3)

ax2.set_ylabel('u [N]')
ax2.set_xlabel('timp [s]')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('ablation_study.png', dpi=150)
print("\nSalvat: ablation_study.png")
