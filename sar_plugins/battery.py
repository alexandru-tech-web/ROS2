#!/usr/bin/env python3
"""battery.py — BatteryModel: energie + failsafe RTL/LAND per drona.

Model simplu si onest pentru multirotor: putere = P_hover + k_v * |v|
(zborul inainte adauga consum aprox. liniar cu viteza la viteze mici-medii).
Masina de stari extinde failsafe-ul distribuit existent (pierderea legaturii
-> aterizare) cu dimensiunea ENERGETICA:

  NORMAL --soc < soc_rtl--> RTL --soc < soc_land sau ajuns acasa--> LAND

Pragul RTL e dinamic optional: tine cont de energia necesara intoarcerii
de la distanta curenta (marja * d / v_rtl * P_zbor), astfel incat dronele
departate de baza intra in RTL mai devreme — leaga energia de geometria
misiunii, la fel cum link-ul radio leaga comunicatia de ea.
"""


class BatteryModel:
    NORMAL, RTL, LAND = "NORMAL", "RTL", "LAND"

    def __init__(self,
                 capacity_wh=60.0,     # ~ baterie 4S 4000 mAh
                 p_hover_w=120.0,      # puterea la punct fix
                 k_v_w=8.0,            # W per m/s de viteza orizontala
                 soc_rtl=0.30,         # prag static RTL
                 soc_land=0.10,        # prag critic — aterizare imediata
                 v_rtl=4.0,            # viteza presupusa la intoarcere [m/s]
                 dynamic_margin=1.5):  # marja energiei de intoarcere (>=1)
        self.capacity_wh = float(capacity_wh)
        self.p_hover_w = float(p_hover_w)
        self.k_v_w = float(k_v_w)
        self.soc_rtl = float(soc_rtl)
        self.soc_land = float(soc_land)
        self.v_rtl = max(float(v_rtl), 0.1)
        self.dynamic_margin = max(float(dynamic_margin), 1.0)
        self.used_wh = 0.0
        self.state = self.NORMAL
        self.t_rtl = None
        self.t_land = None

    # ---- integrarea consumului ----
    def power_w(self, speed):
        return self.p_hover_w + self.k_v_w * abs(float(speed))

    def update(self, dt, speed=0.0, t=None, dist_home=None):
        """Integreaza consumul pe dt [s] la viteza data [m/s]; actualizeaza
        starea. dist_home (optional) activeaza pragul RTL dinamic.
        Intoarce starea curenta."""
        if self.state != self.LAND:
            self.used_wh += self.power_w(speed) * max(float(dt), 0.0) / 3600.0
        soc = self.soc()
        if self.state == self.NORMAL:
            trigger = soc <= self.soc_rtl
            if not trigger and dist_home is not None:
                need_wh = (self.dynamic_margin * self.power_w(self.v_rtl)
                           * (float(dist_home) / self.v_rtl) / 3600.0)
                trigger = soc * self.capacity_wh <= need_wh + \
                    self.soc_land * self.capacity_wh
            if trigger:
                self.state = self.RTL
                self.t_rtl = t
        if self.state in (self.NORMAL, self.RTL) and soc <= self.soc_land:
            self.state = self.LAND
            self.t_land = t
        return self.state

    def reached_home(self, t=None):
        """De apelat cand drona a ajuns la baza in starea RTL."""
        if self.state == self.RTL:
            self.state = self.LAND
            self.t_land = t
        return self.state

    # ---- metrici ----
    def soc(self):
        return max(0.0, 1.0 - self.used_wh / self.capacity_wh)

    def remaining_wh(self):
        return max(0.0, self.capacity_wh - self.used_wh)

    def endurance_s(self, speed=0.0):
        """Cat mai poate zbura la viteza data, pana la soc_land."""
        usable = self.remaining_wh() - self.soc_land * self.capacity_wh
        return max(0.0, 3600.0 * usable / self.power_w(speed))

    CSV_HEADER = "t_s,id,soc,state,used_wh\n"

    def summary(self):
        return {"soc": round(self.soc(), 4), "state": self.state,
                "used_wh": round(self.used_wh, 2),
                "t_rtl": self.t_rtl, "t_land": self.t_land}
