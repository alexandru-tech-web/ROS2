#!/usr/bin/env python3
"""test_v2b_reordonare.py -- V2b: toleranta la reordonare in EstimatorLink (R1-R4). SCRIS INAINTE DE IMPLEMENTARE, 21.09.2026.
Fara ROS, fara retea. tau_r = 100 ms (2 x perioada sondei la 20 Hz), T_sonda = 1.0 s. Pragurile NU se ating: daca 100 ms nu ajunge, e rezultat.
  T0   identitate: observa(seq) FARA timp = comportamentul vechi, bit cu bit (referinta calculata cu codul vechi, seed 7, 2000 pachete, 12 % pierdere)
  V10  reordonare != pierdere (offline): 20 Hz, delay 200 ms + jitter uniform +-50 ms (kernelul aplica uniform, C1), FARA pierdere, 60 s
       -> L_hat < 0.02; n_goluri == 0; creditate > 0 (au existat reordonari); reparate == 0
  T_rep  pachet sosit dupa tau_r si inainte de T_sonda -> 'reparat' (numarat separat), L il numara ca pierdere (R2, R3)
  T_neint pachet care nu mai vine -> dupa T_sonda 'neintors'; L si B pe golurile necreditate (R3, R4)
  T_l15  pierdere Bernoulli 15 % + acelasi jitter, 60 s -> |L_hat - 0.15| <= 20 % relativ (0.03); B pe golurile necreditate ~ 1/(1-0.15)
"""
import os
import random
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AICI), "c3_gateway", "core"))
from estimator import EstimatorLink                                 # noqa: E402

TAU_R, T_SONDA, HZ = 0.100, 1.0, 20.0
REF = dict(L=0.1267097934, B=1.0615702119, n=1999, goluri=221, stable=True)


def t0():
    random.seed(7)
    e = EstimatorLink()
    seq = 0
    for _ in range(2000):
        seq += 1
        if random.random() < 0.12:
            continue
        e.observa(seq)
    est = e.estimare()
    ok = (abs(est.L - REF["L"]) < 1e-9 and abs(est.B - REF["B"]) < 1e-9 and est.n_samples == REF["n"]
          and est.n_goluri == REF["goluri"] and est.stable == REF["stable"])
    return ok, "T0 identitate fara timp: L=%.10f B=%.10f n=%d goluri=%d (ref %.10f / %.10f / %d / %d)" % (
        est.L, est.B, est.n_samples, est.n_goluri, REF["L"], REF["B"], REF["n"], REF["goluri"])


def sosiri(durata, pierdere, seed, delay=0.200, jitter=0.050):
    """(t_sosire, seq) sortate dupa sosire, pentru sonde la HZ cu intarziere uniforma [delay-jitter, delay+jitter] si pierdere Bernoulli."""
    rnd = random.Random(seed)
    L = []
    n = int(durata * HZ)
    for k in range(1, n + 1):
        if rnd.random() < pierdere:
            continue
        L.append((k / HZ + delay + rnd.uniform(-jitter, jitter), k))
    L.sort()
    return L, n


def ruleaza(L, t_final):
    e = EstimatorLink(tau_r=TAU_R, T_sonda=T_SONDA)
    for t, s in L:
        e.observa(s, t)
    e.tick(t_final)
    return e


def v10():
    L, n = sosiri(60.0, 0.0, 11)
    reord = sum(1 for (ta, sa), (tb, sb) in zip(L, L[1:]) if sb < sa)
    e = ruleaza(L, 60.0 + 2.0)
    est = e.estimare()
    ok = est.L < 0.02 and est.n_goluri == 0 and e.n_creditate > 0 and e.n_reparate == 0
    return ok, "V10 reordonare != pierdere: %d inversiuni in sosire; L_hat=%.4f (< 0.02), goluri=%d, creditate=%d, reparate=%d, L_fer=%.4f" % (
        reord, est.L, est.n_goluri, e.n_creditate, e.n_reparate, e.L_fer)


def t_rep():
    e = EstimatorLink(tau_r=TAU_R, T_sonda=T_SONDA)
    t = 0.0
    for s in (1, 2, 3):
        e.observa(s, t); t += 0.05
    e.observa(5, t)                       # 4 lipseste la t=0.15
    e.observa(6, t + 0.05)
    e.observa(4, t + 0.50)                # 4 soseste 0.5 s dupa gol: > tau_r, < T_sonda -> reparat
    e.tick(t + 2.0)
    est = e.estimare()
    ok = e.n_reparate == 1 and e.n_creditate == 0 and est.n_goluri == 1 and est.L > 0.0
    return ok, "T_rep: reparate=%d creditate=%d goluri=%d L=%.4f (pierderea ramane in L, reparatul e separat)" % (
        e.n_reparate, e.n_creditate, est.n_goluri, est.L)


def t_cred():
    e = EstimatorLink(tau_r=TAU_R, T_sonda=T_SONDA)
    e.observa(1, 0.00); e.observa(2, 0.05); e.observa(4, 0.10); e.observa(3, 0.14)     # 3 soseste 40 ms dupa gol -> creditat
    e.observa(5, 0.20); e.tick(3.0)
    est = e.estimare()
    ok = e.n_creditate == 1 and est.n_goluri == 0 and est.L == 0.0 and est.n_samples == 5
    return ok, "T_cred: creditate=%d goluri=%d L=%.4f n=%d" % (e.n_creditate, est.n_goluri, est.L, est.n_samples)


def t_neint():
    e = EstimatorLink(tau_r=TAU_R, T_sonda=T_SONDA)
    e.observa(1, 0.00); e.observa(2, 0.05); e.observa(6, 0.10)      # 3,4,5 lipsesc: un gol de 3
    for k, s in enumerate(range(7, 20)):
        e.observa(s, 0.15 + 0.05 * k)
    e.tick(5.0)
    est = e.estimare()
    ok = est.n_goluri == 1 and e.n_neintoarse == 3 and abs(est.B - (1.0 + 0.2 * (3 - 1.0))) < 1e-9 and est.n_samples == 19            # 16 primite + 3 pierdute (seq 1..19)
    return ok, "T_neint: goluri=%d neintoarse=%d B=%.3f (asteptat 1 + 0.2*(3-1) = 1.400) n=%d (asteptat 19)" % (est.n_goluri, e.n_neintoarse, est.B, est.n_samples)


def t_l15():
    L, n = sosiri(60.0, 0.15, 5)
    e = ruleaza(L, 62.0)
    est = e.estimare()
    ok = abs(est.L - 0.15) <= 0.03
    return ok, "T_l15 pierdere 15 %% + jitter: L_hat=%.4f (|dL| <= 0.03), L_fer=%.4f, B=%.2f, goluri=%d creditate=%d reparate=%d" % (
        est.L, e.L_fer, est.B, est.n_goluri, e.n_creditate, e.n_reparate)


def main():
    rez = [t0(), v10(), t_cred(), t_rep(), t_neint(), t_l15()]
    for ok, txt in rez:
        print("  %s  %s" % ("PASS" if ok else "FAIL", txt))
    print("TESTE V2b %s." % ("OK" if all(ok for ok, _ in rez) else "FAIL"))
    return 0 if all(ok for ok, _ in rez) else 1


if __name__ == "__main__":
    sys.exit(main())
