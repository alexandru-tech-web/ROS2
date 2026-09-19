#!/usr/bin/env python3
"""encoder_core.py -- stratul de ENCODER al bancului: de la impulsuri
cuantizate la viteza si acceleratie CURATE, plus jurnalul pentru grafice.

Problema reala: encoderul da pozitie in pasi (counts). Derivata numerica
bruta a unei pozitii cuantizate = zgomot urias pe viteza (saltul de un
pas / dt) si inutilizabil pe acceleratie. Solutia: filtrul de urmarire
alpha-beta-gamma -- estimeaza simultan pozitie/viteza/acceleratie, fara
numpy/scipy, rulabil si pe Raspberry Pi la 1 kHz.

  EncoderModel        cuantizare la counts_per_rev (+ zgomot optional)
  NaiveDiff           derivata bruta (pentru comparatie in figuri)
  KinematicEstimator  filtrul alpha-beta-gamma (th, om, acc)
  EncoderLogger       CSV "t,pair,th_raw,th,om,acc" (acelasi stil repo)
"""
import math
from datetime import datetime, timezone


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


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
    Exista doar ca martor al problemei -- NU pentru control."""

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


class MotorEncoderBank:
    """Sase canale de encoder independente pentru trei perechi rigide.

    ``signs`` si ``offsets`` aliniaza citirile brute pe axul comun:
    theta_aligned = sign * theta_motor + offset. In simulare semnele sunt
    +1 si offseturile zero; valorile reale se calibreaza pe banc.
    """

    def __init__(self, n_pairs=3, counts_per_rev=4096,
                 alpha=0.25, beta=0.02, gamma=0.0005,
                 signs=None, offsets=None):
        self.n_motors = 2 * int(n_pairs)
        cpr = int(counts_per_rev)
        if self.n_motors <= 0 or cpr < 0:
            raise ValueError("numarul de perechi si CPR trebuie sa fie valide")
        self.signs = list(signs) if signs is not None else [1] * self.n_motors
        self.offsets = ([float(x) for x in offsets] if offsets is not None
                        else [0.0] * self.n_motors)
        if (len(self.signs) != self.n_motors or
                len(self.offsets) != self.n_motors or
                any(s not in (-1, 1) for s in self.signs) or
                any(not math.isfinite(x) for x in self.offsets)):
            raise ValueError("calibrarea encoderelor este invalida")
        self.encoders = ([EncoderModel(cpr) for _ in range(self.n_motors)]
                         if cpr else [None] * self.n_motors)
        self.filters = [KinematicEstimator(alpha, beta, gamma)
                        for _ in range(self.n_motors)]
        self.naive = [NaiveDiff() for _ in range(self.n_motors)]
        self.last_t = [None] * self.n_motors

    def sample(self, motor_id, t, theta_motor):
        """Intoarce None pentru un timestamp vechi; altfel o masura noua."""
        mid = int(motor_id)
        if not 0 <= mid < self.n_motors:
            raise ValueError("motor_id in afara bancului")
        t = float(t)
        theta_motor = float(theta_motor)
        if not math.isfinite(t) or not math.isfinite(theta_motor):
            raise ValueError("masura encoderului trebuie sa fie finita")
        previous = self.last_t[mid]
        if previous is not None and t <= previous:
            return None
        dt = t - previous if previous is not None else 0.005
        self.last_t[mid] = t
        aligned = self.signs[mid] * theta_motor + self.offsets[mid]
        encoder = self.encoders[mid]
        counts = encoder.counts(aligned) if encoder is not None else None
        th_raw = counts * encoder.step if encoder is not None else aligned
        om_raw, _ = self.naive[mid].step(th_raw, dt)
        th, om, acc = self.filters[mid].step(th_raw, dt)
        return {"t": t, "counts": counts, "th_raw": th_raw,
                "th": th, "om": om, "acc": acc, "om_raw": om_raw}


class EncoderLogger:
    CSV_HEADER = "t_s,time_utc,pair,th_raw,th,om,acc\n"

    def __init__(self, path):
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        # Un jurnal de cercetare nu se suprascrie implicit. Modul ``x``
        # esueaza explicit daca numele a mai fost folosit.
        self.f = open(path, "x", encoding="utf-8", buffering=1)
        self.f.write(self.CSV_HEADER)

    def row(self, t, pair, th_raw, th, om, acc, time_utc=None):
        self.f.write(f"{t:.4f},{time_utc or utc_timestamp()},{pair},"
                     f"{th_raw:.6f},{th:.6f},"
                     f"{om:.5f},{acc:.4f}\n")

    def close(self):
        self.f.flush()
        self.f.close()


class MotorEncoderLogger:
    """CSV separat pentru toate cele sase citiri, fara suprascriere."""

    CSV_HEADER = ("t_s,time_utc,pair,side,motor_id,counts,th_raw,th,"
                  "om,acc,om_raw,source\n")

    def __init__(self, path):
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.f = open(path, "x", encoding="utf-8", buffering=1)
        self.f.write(self.CSV_HEADER)

    def row(self, pair, side, measurement, time_utc=None, source="unknown"):
        mid = 2 * int(pair) + (side == "B")
        counts = measurement["counts"]
        count_text = "" if counts is None else str(counts)
        self.f.write(
            f'{measurement["t"]:.4f},{time_utc or utc_timestamp()},'
            f'{pair},{side},{mid},{count_text},'
            f'{measurement["th_raw"]:.6f},{measurement["th"]:.6f},'
            f'{measurement["om"]:.5f},{measurement["acc"]:.4f},'
            f'{measurement["om_raw"]:.5f},{source}\n')

    def close(self):
        self.f.flush()
        self.f.close()
