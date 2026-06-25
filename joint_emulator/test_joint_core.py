#!/usr/bin/env python3
"""Bateria de verificari a emulatorului de articulatie (fara ROS/fier)."""
import math

from joint_core import (ImpedanceLaw, VirtualLimb, DelayLine, PairSim,
                        EnergyMonitor, SafetyGate, run_equilibrium)
from drive_iface import SimBackend

OK = 0


def ck(cond, msg):
    global OK
    assert cond, msg
    OK += 1
    print(f"[ok]   {msg}")


# ---- legea de impedanta ----
law = ImpedanceLaw(k_nm_rad=10, b_nms_rad=0.5, tau_max=1.5)
ck(law.torque(0.0, 0.0) == 0.0, "impedanta: zero la echilibru")
ck(law.torque(0.2, 0.0) < 0, "impedanta: se opune deplasarii pozitive")
ck(law.torque(-0.2, 0.0) > 0, "impedanta: se opune deplasarii negative")
ck(abs(law.torque(10.0, 0.0)) == 1.5, "impedanta: clamp la tau_max")
law_db = ImpedanceLaw(k_nm_rad=10, deadband_rad=0.05)
ck(law_db.torque(0.03, 0.0) == 0.0, "impedanta: deadband ignora eroarea mica")
law_r = ImpedanceLaw(k_nm_rad=100, tau_max=5, ramp_nm_s=10)
t1 = law_r.torque(1.0, 0.0, dt=0.01)
ck(abs(t1) <= 0.1 + 1e-9, "impedanta: rampa limiteaza saltul de cuplu")

# ---- pacientul virtual (catch spastic) ----
limb = VirtualLimb(k=2, b=0.2, catch_om=1.0, catch_gain=5)
lent = abs(limb.torque(0.1, 0.5))
rapid = abs(limb.torque(0.1, 1.5))
ck(rapid > lent * 2, "limb: rezistenta creste brusc peste viteza-prag (catch)")
ck(abs(limb.torque(5, 5)) <= limb.tau_max, "limb: clamp la tau_max")

# ---- intarzierea ----
dl = DelayLine(0.01, dt=0.001, initial=0.0)
outs = [dl.push(float(i)) for i in range(15)]
ck(outs[0] == 0.0 and outs[10] == 0.0 and outs[11] == 1.0,
   "delay: 10 ms = 10 esantioane la 1 kHz")

# ---- fizica perechii: B tine echilibrul sub treapta lui A ----
sim, mon, tr = run_equilibrium(
    lambda t: 0.5 if t > 0.2 else 0.0,
    ImpedanceLaw(k_nm_rad=10, b_nms_rad=0.6, tau_max=2.0), t_end=4.0)
th_fin = sim.th
ck(abs(th_fin - 0.05) < 0.01,
   f"echilibru: th_final~=tau/K (={th_fin:.3f} rad la 0.5 Nm / 10 Nm/rad)")
ck(abs(sim.om) < 0.02, "echilibru: viteza finala ~0 (amortizat)")

# ---- pasivitate: fara intarziere energia B e marginita ----
ck(mon.e_max < 0.05, f"pasivitate: energia injectata de B marginita ({mon.e_max:.4f} J)")

# ---- CARLIGUL TEZEI: intarzierea destabilizeaza aceeasi lege ----
def energie_la(delay_ms):
    _, m, _ = run_equilibrium(
        lambda t: 0.5 if t > 0.2 else 0.0,
        ImpedanceLaw(k_nm_rad=40, b_nms_rad=1.2, tau_max=8.0),
        dt=0.001, t_end=3.0, delay_s=delay_ms / 1000.0)
    return m.e_max

e0, e20, e60 = energie_la(0), energie_la(20), energie_la(60)
ck(e0 < 0.05, f"stabil la 0 ms (E={e0:.3f} J)")
ck(e60 > 10 * max(e0, 1e-6), f"instabil la 60 ms (E={e60:.1f} J >> E0)")
ck(e60 > e20, f"degradare monotona cu intarzierea ({e20:.3f} -> {e60:.1f} J)")

# ---- siguranta: watchdog -> cuplu zero ----
g = SafetyGate(timeout_s=0.05, tau_max=2.0)
g.feed(0.0)
ck(g.gate(0.02, 1.0) == 1.0, "watchdog: trece cand masura e proaspata")
ck(g.gate(0.2, 1.0) == 0.0 and g.tripped, "watchdog: cuplu ZERO cand encoderul tace")
ck(g.gate(0.21, -5.0) == 0.0, "watchdog: ramane declansat")

# ---- backend-ul simulat respecta contractul ----
hw = SimBackend(n_pairs=3)
hw.enable(0); hw.enable(1)            # perechea 0: A=0, B=1
hw.set_torque(0, 0.5)
law_b = ImpedanceLaw(k_nm_rad=10, b_nms_rad=0.6, tau_max=2.0)
for _ in range(3000):
    t, th, om = hw.read(1)
    hw.set_torque(1, law_b.torque(th, om, 0.001))
ck(abs(th - 0.05) < 0.012, f"backend sim: aceeasi fizica prin interfata ({th:.3f} rad)")
t2, th2, _ = hw.read(3)               # perechea 1 neatinsa
ck(abs(th2) < 1e-9, "backend sim: perechile sunt independente")
hw.estop()
ck(not any(any(e) for e in hw.enabled), "estop: dezarmeaza tot")


# ---- tele-impedanta: canalul degradat + legea adaptiva ----
from teleimpedance import DegradedMeasure, AdaptiveImpedance, run_teleimpedance

lk = DegradedMeasure(ms=50, seed=1)
lk.push(0.0, 0.7, 0.1)
ck(lk.latest(0.02) is None, "link: nimic livrat inainte de latenta")
th_m, om_m, age = lk.latest(0.06)
ck(th_m == 0.7 and 0.055 < age < 0.065, "link: livrare dupa 50 ms, varsta corecta")
lk2 = DegradedMeasure(loss=1.0, seed=1)
lk2.push(0.0, 1.0, 0.0)
ck(lk2.latest(1.0) is None, "link: loss=1 nu livreaza nimic")

TAU = lambda t: 0.5 if t > 0.2 else 0.0
law_ad = AdaptiveImpedance(k0=40, b0=1.2, tau_max=8.0)
s_ad, m_ad, _ = run_teleimpedance(law_ad, DegradedMeasure(ms=60, seed=42),
                                  TAU, t_end=4.0, adaptive=True)
ck(m_ad.e_max < 0.01, f"adaptiv+amortizare locala: pasiv la 60 ms (E={m_ad.e_max:.4f} J)")
ck(abs(s_ad.th - 0.5 / law_ad.k_ef) < 0.01,
   f"adaptiv: echilibru la tau/K_ef ({s_ad.th:.3f} rad, K_ef={law_ad.k_ef:.1f})")
s_120, m_120, _ = run_teleimpedance(AdaptiveImpedance(k0=40, b0=1.2, tau_max=8.0),
                                    DegradedMeasure(ms=120, seed=42),
                                    TAU, t_end=4.0, adaptive=True)
ck(m_120.e_max < 0.01, f"adaptiv: ramane pasiv si la 120 ms (E={m_120.e_max:.4f} J)")
law_fx = ImpedanceLaw(k_nm_rad=40, b_nms_rad=1.2, tau_max=8.0)
_, m_fx, _ = run_teleimpedance(law_fx, DegradedMeasure(ms=60, seed=42),
                               TAU, t_end=4.0)
ck(m_fx.e_max > 1000 * max(m_ad.e_max, 1e-6),
   f"duelul: fixul-total-remote explodeaza unde adaptivul rezista "
   f"({m_fx.e_max:.0f} J vs {m_ad.e_max:.4f} J)")


# ---- stratul de encoder: cuantizare + estimator ----
from encoder_core import EncoderModel, NaiveDiff, KinematicEstimator

enc = EncoderModel(counts_per_rev=4096)
ck(abs(enc.step - 2 * math.pi / 4096) < 1e-12, "encoder: pasul = 2pi/cpr")
ck(enc.read(0.0) == 0.0 and abs(enc.read(enc.step * 3.4) - enc.step * 3) < 1e-12,
   "encoder: cuantizare la cel mai apropiat pas")

A, F = 0.5, 1.0
W = 2 * math.pi * F
nd, ke = NaiveDiff(), KinematicEstimator()
dt = 0.001
e_n, e_k, e_a = [], [], []
t = 0.0
while t < 3.0:
    th_m = enc.read(A * math.sin(W * t))
    om_n, _ = nd.step(th_m, dt)
    _, om_k, acc_k = ke.step(th_m, dt)
    if t > 0.5:
        e_n.append((om_n - A * W * math.cos(W * t)) ** 2)
        e_k.append((om_k - A * W * math.cos(W * t)) ** 2)
        e_a.append((acc_k + A * W * W * math.sin(W * t)) ** 2)
    t += dt
rms = lambda e: (sum(e) / len(e)) ** 0.5
ck(rms(e_k) < 0.05, f"estimator: viteza filtrata RMS={rms(e_k):.3f} rad/s (<1.6% din varf)")
ck(rms(e_n) > 10 * rms(e_k),
   f"estimator: de >10x mai curat decat derivata bruta ({rms(e_n):.2f} vs {rms(e_k):.3f})")
ck(rms(e_a) < 0.15 * A * W * W,
   f"estimator: acceleratia RMS={rms(e_a):.2f} (<15% din varful {A*W*W:.1f})")
ke2 = KinematicEstimator()
for _ in range(2000):
    ke2.step(0.7, 0.001)
ck(abs(ke2.th - 0.7) < 1e-3 and abs(ke2.om) < 1e-3 and abs(ke2.acc) < 0.05,
   "estimator: pe pozitie constanta converge la om=0, acc=0")

print(f"\n=== {OK}/{OK} verificari trecute ===")
