#!/usr/bin/env python3
"""encoder_core.py — stratul de ENCODER al bancului: de la impulsuri
cuantizate la viteza si acceleratie CURATE, plus jurnalul pentru grafice.

Problema reala: encoderul da pozitie in pasi (counts). Derivata numerica
bruta a unei pozitii cuantizate = zgomot urias pe viteza (saltul de un
pas / dt) si inutilizabil pe acceleratie. Solutia: filtrul de urmarire
alpha-beta-gamma — estimeaza simultan pozitie/viteza/acceleratie, fara
numpy/scipy, rulabil si pe Raspberry Pi la 1 kHz.

  EncoderModel        cuantizare la counts_per_rev (+ zgomot optional)
  NaiveDiff           derivata bruta (pentru comparatie in figuri)
  KinematicEstimator  filtrul alpha-beta-gamma (th, om, acc)
  EncoderLogger       CSV "t,pair,th_raw,th,om,acc" (acelasi stil repo)
"""
import math


class EncoderModel:
    """Encoderul real: pozitia adevarata -> counts -> pozitia cuantizata."""

    def __init__(self, counts_per_rev=4096, noise_counts=0.0, seed=None):
        self.cpr = int(counts_per_rev)
        self.step = 2.0 * math.pi / self.cpr
        self.noise = float(noise_counts)
        if seed is not None:
            import random
            self.rng = random.Random(seed)
        else:
            self.rng = None

    def counts(self, th_true):
        c = th_true / self.step
        if self.noise > 0 and self.rng:
            c += self.rng.gauss(0.0, self.noise)
        return int(round(c))

    def read(self, th_true):
        return self.counts(th_true) * self.step


class NaiveDiff:
    """Derivata bruta: (x - x_prec)/dt, de doua ori pentru acceleratie.
    Exista doar ca martor al problemei — NU pentru control."""

    def __init__(self):
        self.th_p = None
        self.om_p = 0.0

    def step(self, th, dt):
        om = 0.0 if self.th_p is None else (th - self.th_p) / dt
        acc = (om - self.om_p) / dt if self.th_p is not None else 0.0
        self.th_p, self.om_p = th, om
        return om, acc


class KinematicEstimator:
    """Filtrul alpha-beta-gamma: urmareste (th, om, acc) din pozitia
    cuantizata. Predictie cinematica + corectie pe reziduu. Castigurile
    implicite sunt acordate pentru 1 kHz / 4096 cpr; pentru alte rate,
    porneste de la aceleasi valori si creste-le daca raspunsul e lent."""

    def __init__(self, alpha=0.25, beta=0.02, gamma=0.0005,
                 th0=0.0, om0=0.0, acc0=0.0):
        self.a, self.b, self.g = float(alpha), float(beta), float(gamma)
        self.th, self.om, self.acc = float(th0), float(om0), float(acc0)
        self._init = False

    def step(self, th_meas, dt):
        if not self._init:
            self.th, self._init = float(th_meas), True
            return self.th, self.om, self.acc
        th_p = self.th + self.om * dt + 0.5 * self.acc * dt * dt
        om_p = self.om + self.acc * dt
        r = th_meas - th_p
        self.th = th_p + self.a * r
        self.om = om_p + (self.b / dt) * r
        self.acc = self.acc + (2.0 * self.g / (dt * dt)) * r
        return self.th, self.om, self.acc


class EncoderLogger:
    CSV_HEADER = "t_s,pair,th_raw,th,om,acc\n"

    def __init__(self, path):
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.f = open(path, "w")
        self.f.write(self.CSV_HEADER)

    def row(self, t, pair, th_raw, th, om, acc):
        self.f.write(f"{t:.4f},{pair},{th_raw:.6f},{th:.6f},"
                     f"{om:.5f},{acc:.4f}\n")

    def close(self):
        self.f.flush()
        self.f.close()
