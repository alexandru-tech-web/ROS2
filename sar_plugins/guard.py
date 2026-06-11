#!/usr/bin/env python3
"""guard.py — ObstacleGuard: oprire/franare autonoma la obstacol, pe lidar.

Al treilea strat de siguranta al roverului, dupa watchdog si respingerea
comenzilor invechite: chiar daca operatorul comanda inainte printr-un link
degradat (sau comanda veche "scapa" prin canal), roverul NU avanseaza spre
un obstacol aflat sub d_stop si franeaza progresiv sub d_slow.

Logica pe sectorul frontal al scanarii (sector_deg in jurul axei x a
robotului), cu histerezis: odata oprit, cere d > d_stop * release_factor
ca sa elibereze — evita oscilatia pe muchia pragului. Rotatia pe loc si
mersul inapoi raman permise (operatorul poate iesi singur din situatie).
"""
import math


class ObstacleGuard:
    def __init__(self, d_stop=0.6, d_slow=1.5, sector_deg=70.0,
                 release_factor=1.25, range_min_valid=0.05):
        assert d_slow >= d_stop > 0
        self.d_stop = float(d_stop)
        self.d_slow = float(d_slow)
        self.half_sector = math.radians(float(sector_deg)) / 2.0
        self.release_factor = max(float(release_factor), 1.0)
        self.range_min_valid = float(range_min_valid)
        self.blocked = False           # starea de histerezis
        self.last_min = float("inf")

    # ---- procesarea scanarii ----
    def min_front(self, ranges, angle_min, angle_inc):
        """Distanta minima valida in sectorul frontal [-half, +half].
        Ignora inf/nan/0 si valorile sub range_min_valid (lovituri pe sasiu).
        Unghiurile se normalizeaza in (-pi, pi] ca sa accepte si scanari
        0..2*pi si -pi..pi."""
        best = float("inf")
        a = float(angle_min)
        for r in ranges:
            ang = math.atan2(math.sin(a), math.cos(a))   # normalizare
            a += float(angle_inc)
            if abs(ang) > self.half_sector:
                continue
            try:
                rv = float(r)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(rv) or rv < self.range_min_valid:
                continue
            if rv < best:
                best = rv
        self.last_min = best
        return best

    # ---- filtrarea comenzii ----
    def filter_cmd(self, v, w, dmin=None):
        """Aplica garda pe comanda (v, w). dmin implicit = ultima scanare.
        Intoarce (v_filtrat, w, info_dict)."""
        d = self.last_min if dmin is None else float(dmin)
        v = float(v)
        # actualizarea histerezisului
        if self.blocked:
            if d > self.d_stop * self.release_factor:
                self.blocked = False
        elif d <= self.d_stop:
            self.blocked = True

        scale = 1.0
        if v > 0.0:                    # doar inaintarea e limitata
            if self.blocked:
                scale = 0.0
            elif d < self.d_slow:
                scale = (d - self.d_stop) / max(self.d_slow - self.d_stop,
                                                1e-6)
                scale = min(max(scale, 0.0), 1.0)
        v_out = v * scale
        info = {"dmin": None if math.isinf(d) else round(d, 3),
                "scale": round(scale, 3), "blocked": self.blocked}
        return v_out, float(w), info
