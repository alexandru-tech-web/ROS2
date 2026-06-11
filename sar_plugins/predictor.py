#!/usr/bin/env python3
"""predictor.py — DeadReckoningPredictor: "fantoma" predictiva a roverului.

Tehnica clasica de teleoperare (predictive display, Sheridan): operatorul
nu vede pozitia VECHE (intarziata de link), ci o predictie a pozitiei
CURENTE, obtinuta integrand inainte comenzile pe care chiar el le-a trimis
de la momentul ultimei poze primite.

Implementare: pastram istoricul comenzilor trimise (t, v, w); la sosirea
unei poze cu timestamp t_pose (varsta = t_now - t_pose), integram modelul
uniciclu exact (pe arc, nu Euler) peste comenzile din intervalul
[t_pose, t_now]. Eroarea predictiei fata de adevarul-teren e metrica de
articol: cat de mult reduce predictia eroarea perceputa de operator,
ca functie de latenta.
"""
import bisect
import math
from collections import deque


def unicycle_step(x, y, th, v, w, dt):
    """Integrarea exacta a modelului uniciclu pe un pas dt cu (v, w) const."""
    if dt <= 0.0:
        return x, y, th
    if abs(w) < 1e-9:
        return x + v * math.cos(th) * dt, y + v * math.sin(th) * dt, th
    th2 = th + w * dt
    r = v / w
    return (x + r * (math.sin(th2) - math.sin(th)),
            y - r * (math.cos(th2) - math.cos(th)),
            th2)


class CmdHistory:
    """Istoric (t, v, w) ordonat in timp, cu fereastra maxima [s]."""

    def __init__(self, horizon_s=5.0):
        self.horizon_s = float(horizon_s)
        self.buf = deque()             # (t, v, w)

    def add(self, t, v, w):
        t = float(t)
        if self.buf and t < self.buf[-1][0]:
            return                     # ignoram timpii care merg inapoi
        self.buf.append((t, float(v), float(w)))
        tmin = t - self.horizon_s
        while len(self.buf) > 1 and self.buf[1][0] <= tmin:
            self.buf.popleft()

    def segment(self, t_from, t_to):
        """Lista [(t_start, t_end, v, w), ...] care acopera exact
        [t_from, t_to] cu comanda activa pe fiecare subinterval (zero-order
        hold). Daca nu exista comenzi inainte de t_from, primul subinterval
        foloseste (0, 0)."""
        if t_to <= t_from:
            return []
        ts = [b[0] for b in self.buf]
        segs = []
        # comanda activa la t_from = ultima cu t <= t_from
        i = bisect.bisect_right(ts, t_from) - 1
        t_cur = t_from
        while t_cur < t_to:
            if i < 0:
                v, w = 0.0, 0.0
            else:
                _, v, w = self.buf[i]
            t_next = self.buf[i + 1][0] if i + 1 < len(self.buf) else t_to
            t_end = min(max(t_next, t_cur), t_to)
            if t_end > t_cur:
                segs.append((t_cur, t_end, v, w))
            t_cur = t_end
            i += 1
            if i >= len(self.buf) and t_cur < t_to:
                segs.append((t_cur, t_to, v, w))
                break
        return segs


class DeadReckoningPredictor:
    def __init__(self, horizon_s=5.0, max_extrapolation_s=2.0):
        self.hist = CmdHistory(horizon_s)
        self.max_extrap = float(max_extrapolation_s)
        self.last_pose = None          # (t, x, y, th)

    def on_cmd_sent(self, t, v, w):
        self.hist.add(t, v, w)

    def on_pose(self, t_pose, x, y, th):
        if self.last_pose is None or t_pose >= self.last_pose[0]:
            self.last_pose = (float(t_pose), float(x), float(y), float(th))

    def predict(self, t_now):
        """Predictia pozei la t_now. Intoarce (x, y, th, age_s, extrap_s)
        sau None daca nu avem inca nicio poza."""
        if self.last_pose is None:
            return None
        t0, x, y, th = self.last_pose
        age = max(0.0, float(t_now) - t0)
        extrap = min(age, self.max_extrap)
        for (ta, tb, v, w) in self.hist.segment(t0, t0 + extrap):
            x, y, th = unicycle_step(x, y, th, v, w, tb - ta)
        return x, y, th, age, extrap
