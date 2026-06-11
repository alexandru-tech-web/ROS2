#!/usr/bin/env python3
"""victims.py — VictimField: victime simulate + detectie probabilistica.

Plaseaza N victime in aria misiunii (reproductibil, cu seed). O drona aflata
in raza senzorului detecteaza o victima ca proces Poisson cu rata
p_detect [1/s]:  P(detectie in dt) = 1 - exp(-p_detect * dt).
Cu p_detect mare detectia devine practic instantanee la intrarea in raza —
util pentru teste deterministe.

Metricile pe care le produce sunt cele cerute de articolul de rezilienta:
timp-pana-la-prima-detectie, timp-pana-la-toate, numarul de detectii in timp
— toate comparabile intre scenarii de degradare si intre RMW-uri.
"""
import math
import random


class VictimField:
    def __init__(self, n, xmin, xmax, ymin, ymax, seed=0, min_sep=3.0):
        self.rng = random.Random(seed)
        self.bounds = (float(xmin), float(xmax), float(ymin), float(ymax))
        self.victims = self._spawn(int(n), float(min_sep))
        self.detected = {}             # idx -> (t, drone_id)

    def _spawn(self, n, min_sep):
        xmin, xmax, ymin, ymax = self.bounds
        pts = []
        tries = 0
        while len(pts) < n and tries < 200 * max(n, 1):
            tries += 1
            x = self.rng.uniform(xmin, xmax)
            y = self.rng.uniform(ymin, ymax)
            if all((x - px) ** 2 + (y - py) ** 2 >= min_sep ** 2
                   for px, py in pts):
                pts.append((x, y))
        return pts

    # ---- pasul de detectie ----
    def step(self, t, drone_positions, sensor_r, p_detect, dt):
        """drone_positions: dict id -> (x, y[, z]); foloseste doar x, y
        (raza senzorului e proiectia la sol). Intoarce lista de evenimente
        noi: [{"victim": i, "t": t, "by": id, "x":.., "y":..}, ...]."""
        events = []
        r2 = float(sensor_r) ** 2
        p_dt = 1.0 - math.exp(-max(float(p_detect), 0.0) * max(float(dt), 0.0))
        for i, (vx, vy) in enumerate(self.victims):
            if i in self.detected:
                continue
            for did, p in drone_positions.items():
                dx, dy = float(p[0]) - vx, float(p[1]) - vy
                if dx * dx + dy * dy <= r2 and self.rng.random() < p_dt:
                    self.detected[i] = (float(t), did)
                    events.append({"victim": i, "t": round(float(t), 2),
                                   "by": did,
                                   "x": round(vx, 2), "y": round(vy, 2)})
                    break
        return events

    # ---- metrici ----
    @property
    def n_total(self):
        return len(self.victims)

    @property
    def n_detected(self):
        return len(self.detected)

    def first_detection_t(self):
        return min((t for t, _ in self.detected.values()), default=None)

    def last_detection_t(self):
        if len(self.detected) < self.n_total:
            return None
        return max(t for t, _ in self.detected.values())

    def positions(self):
        return [{"victim": i, "x": round(x, 2), "y": round(y, 2),
                 "detected": i in self.detected}
                for i, (x, y) in enumerate(self.victims)]

    CSV_HEADER = "t_s,victim,by,x,y\n"

    def summary(self):
        return {"total": self.n_total, "detected": self.n_detected,
                "t_first": self.first_detection_t(),
                "t_all": self.last_detection_t()}
