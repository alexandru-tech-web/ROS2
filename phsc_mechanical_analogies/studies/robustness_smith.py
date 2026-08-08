#!/usr/bin/env python3
"""
robustness_smith.py
Cat de mult din performanta predictorului Smith este reala si cat este
artefact al faptului ca predictorul si planta impart exact acelasi model?

In ablation_study.py, predictorul foloseste np.interp pe bufferul de comenzi,
iar planta (DelayedCartPole.get_delayed_control) foloseste tot np.interp pe
istoricul ei. Deci canalul este prezis PERFECT. Pe hardware real asta nu se
intampla niciodata: canalul livreaza pachete discrete (ZOH), latenta estimata
difera de cea adevarata, iar parametrii fizici sunt aproximativi.

Testam trei surse de nepotrivire, separat si combinat:
  A. forma canalului   -- predictor ZOH vs planta cu interpolare
  B. latenta estimata  -- tau_est != tau_real (+/- procente)
  C. parametrii plantei-- masa/lungime gresite in modelul de predictie
"""

import numpy as np
import _context  # noqa: F401  -- pachetul importabil si din sursa
from phsc_mechanical_analogies.cartpole_model import CartPoleModel, DelayedCartPole

DT = 0.01
DT_SIM = 0.001
T_END = 5.0
X0 = np.array([0.0, 0.0, 0.10, 0.0])
FAIL = np.pi / 2
N_PRED = 20

plant_model = CartPoleModel()          # planta 'adevarata'
K = plant_model.lqr_gain()


def smith_zoh(model, x0, tau, buf, t, n=N_PRED):
    """Predictor Smith cu zero-order hold (pachete discrete), nu interpolare."""
    if tau <= 0:
        return x0.copy()
    dtp = tau / n
    x = x0.copy()
    for k in range(n):
        target = t + k * dtp - tau
        u = 0.0
        for (ts, us) in reversed(buf):
            if ts <= target:
                u = us
                break
        x = model.dynamics_rk4(x, u, dtp)
    return x


def run(tau_real, tau_est_factor=1.0, pred_model=None, zoh=False, T=T_END):
    pm = pred_model if pred_model is not None else plant_model
    plant = DelayedCartPole()
    x = X0.copy()
    t, u_cmd, t_next = 0.0, 0.0, 0.0
    buf = []
    fell = None
    th_max = 0.0

    while t < T:
        if t >= t_next:
            tau_e = tau_real * tau_est_factor
            if zoh:
                xh = smith_zoh(pm, x, tau_e, buf, t)
            else:
                xh = pm.predict_state_smith(x, tau_e, buf, t, N_PRED)
            u_cmd = float(np.clip(-(K @ xh)[0], -100.0, 100.0))
            buf.append((t, u_cmd))
            if len(buf) > 2000:
                del buf[:-2000]
            t_next = t + DT

        plant.control_history.append((t, u_cmd))
        u_app = plant.get_delayed_control(t, tau_real)
        x = plant.dynamics_rk4(x, u_app, DT_SIM)
        th_max = max(th_max, abs(x[2]))
        if fell is None and abs(x[2]) > FAIL:
            fell = t
        t += DT_SIM

    stabil = fell is None and abs(x[2]) < np.radians(5)
    return stabil, np.degrees(th_max), fell


def sweep(nume, **kw):
    taus = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
    ok = []
    cels = []
    for tau in taus:
        s, thm, f = run(tau, **kw)
        cels.append(f"{thm:6.1f}d" if s else "  cazut")
        if s:
            ok.append(tau)
    prag = f"{max(ok)*1000:.0f}+ ms" if ok else "instabil"
    if ok:
        urm = [t for t in taus if t > max(ok)]
        if urm:
            prag = f"{max(ok)*1000:.0f}-{min(urm)*1000:.0f} ms"
    print(f"  {nume:<42} " + " ".join(cels) + f"   -> prag {prag}")
    return ok


print("=" * 104)
print("ROBUSTETEA PREDICTORULUI SMITH la nepotriviri model-realitate")
print("=" * 104)
print(f"  {'conditie':<42} " +
      " ".join(f"{int(t*1000):>7}" for t in
               [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]) + "   (tau ms)")
print("-" * 104)

sweep("0. ideal (predictor = planta, interpolare)")
sweep("A. canal ZOH (predictor discret)", zoh=True)
sweep("B1. tau subestimat cu 20%", tau_est_factor=0.8)
sweep("B2. tau supraestimat cu 20%", tau_est_factor=1.2)
sweep("B3. tau subestimat cu 50%", tau_est_factor=0.5)

m_gresit = CartPoleModel(M=1.3, m=0.13, L=0.55, b=0.15)   # +30% masa, +10% L
sweep("C. parametri fizici gresiti (+30% M)", pred_model=m_gresit)

print("-" * 104)
sweep("D. combinat: ZOH + tau -20% + param gresiti",
      zoh=True, tau_est_factor=0.8, pred_model=m_gresit)
print("=" * 104)
print()
print("Interpretare: linia 0 este limita superioara optimista (predictor")
print("perfect). Linia D este scenariul realist pentru hardware. Diferenta")
print("dintre ele este marja pe care NU o ai pe robot real.")
