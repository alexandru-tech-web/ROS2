#!/usr/bin/env python3
"""
test_smith_variable.py
LQR + Smith cu latenta VARIABILA sinusoidal 50-150 ms.

Tinta ceruta: theta_rms < 2 grade, |theta|max < 15 grade.

Doua scenarii, pentru ca diferenta dintre ele este exact intrebarea deschisa
inainte de hardware:
  ORACLE    -- controllerul cunoaste tau(t) exact (limita superioara)
  ESTIMAT   -- controllerul foloseste un tau estimat cu EWMA din masuratori
               RTT zgomotoase, exact ca nodul latency_estimator

Al doilea scenariu este cel care conteaza: in runda 3 s-a masurat ca o eroare
de +/-20% pe tau injumatateste marja de stabilitate. Aici verificam daca
estimatorul chiar sta in +/-20% cand tau se misca.
"""

import numpy as np
import _context  # noqa: F401  -- pachetul importabil si din sursa
from phsc_mechanical_analogies.cartpole_model import CartPoleModel, DelayedCartPole

DT = 0.01           # controller 100 Hz
DT_SIM = 0.001
T_END = 10.0
X0 = np.array([0.0, 0.0, 0.10, 0.0])
N_PRED = 20
FAIL = np.pi / 2

# tau(t): sinusoidal 50-150 ms, perioada 4 s
TAU = lambda t: 0.100 + 0.050 * np.sin(2.0 * np.pi * t / 4.0)

model = CartPoleModel()
K = model.lqr_gain()
rng = np.random.default_rng(42)


class EwmaEstimator:
    """Acelasi algoritm ca nodul latency_estimator (EWMA pe RTT/2)."""

    def __init__(self, alpha=0.3, tau0=0.05, rate=20.0, jitter=0.004):
        self.alpha = alpha
        self.tau = tau0
        self.period = 1.0 / rate
        self.jitter = jitter
        self.t_next = 0.0

    def update(self, t, tau_true):
        if t < self.t_next:
            return self.tau
        self.t_next = t + self.period
        # masuratoare RTT zgomotoasa: 2*tau + jitter gaussian
        rtt = 2.0 * tau_true + rng.normal(0.0, self.jitter)
        rtt = max(0.0, rtt)
        self.tau = self.alpha * (0.5 * rtt) + (1 - self.alpha) * self.tau
        return self.tau


def run(mode):
    plant = DelayedCartPole()
    x = X0.copy()
    t, u_cmd, t_next = 0.0, 0.0, 0.0
    buf = []
    est = EwmaEstimator()
    ths, errs = [], []
    fell = None

    while t < T_END:
        tau_true = TAU(t)
        tau_used = tau_true if mode == 'oracle' else est.update(t, tau_true)

        if t >= t_next:
            xh = model.predict_state_smith(x, tau_used, buf, t, N_PRED)
            u_cmd = float(np.clip(-(K @ xh)[0], -100.0, 100.0))
            buf.append((t, u_cmd))
            if len(buf) > 3000:
                del buf[:-3000]
            t_next = t + DT
            if t > 1.0:   # dupa convergenta initiala a estimatorului
                errs.append((tau_used - tau_true) / tau_true)

        plant.control_history.append((t, u_cmd))
        u_app = plant.get_delayed_control(t, tau_true)
        x = plant.dynamics_rk4(x, u_app, DT_SIM)
        ths.append(x[2])
        if fell is None and abs(x[2]) > FAIL:
            fell = t
        t += DT_SIM

    ths = np.array(ths)
    errs = np.array(errs) if errs else np.array([0.0])
    return {
        'th_rms': np.degrees(np.sqrt((ths ** 2).mean())),
        'th_max': np.degrees(np.abs(ths).max()),
        'fell': fell,
        'err_mean': 100 * errs.mean(),
        'err_max': 100 * np.abs(errs).max(),
        'err_p95': 100 * np.percentile(np.abs(errs), 95),
    }


print("=" * 76)
print(f"LQR + Smith, tau(t) sinusoidal 50-150 ms (perioada 4 s), "
      f"controller {1/DT:.0f} Hz, {T_END:.0f} s")
print("=" * 76)
print(f"{'scenariu':<34} {'theta rms':>10} {'|theta|max':>11}  verdict")
print("-" * 76)

TINTA_RMS, TINTA_MAX = 2.0, 15.0
rez = {}
for mode, nume in (('oracle', 'ORACLE (tau cunoscut exact)'),
                   ('ewma', 'ESTIMAT (EWMA din RTT zgomotos)')):
    r = run(mode)
    rez[mode] = r
    ok = (r['fell'] is None and r['th_rms'] < TINTA_RMS
          and r['th_max'] < TINTA_MAX)
    v = "TINTA ATINSA" if ok else (
        f"CAZUT la {r['fell']:.2f}s" if r['fell'] else "SUB TINTA")
    print(f"{nume:<34} {r['th_rms']:>9.2f}d {r['th_max']:>10.2f}d  {v}")

print("-" * 76)
print(f"Tinta ceruta: theta_rms < {TINTA_RMS:.0f} grade, "
      f"|theta|max < {TINTA_MAX:.0f} grade")
print()
e = rez['ewma']
print("Acuratetea estimatorului EWMA (dupa 1 s de convergenta):")
print(f"  eroare medie   : {e['err_mean']:+6.2f} %")
print(f"  eroare p95     : {e['err_p95']:6.2f} %")
print(f"  eroare maxima  : {e['err_max']:6.2f} %")
prag = 20.0
print(f"  prag critic din runda 3: +/-{prag:.0f} %  -> "
      f"{'IN LIMITE' if e['err_p95'] < prag else 'PESTE LIMITE'}")
print("=" * 76)
