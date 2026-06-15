#!/usr/bin/env python3
"""radio_link.py — LogDistanceRadioLink: degradarea legaturii ca functie
de DISTANTA fata de statia de sol (GCS), nu doar din scenarii YAML statice.

Modelul (standard in literatura radio, Rappaport cap. 4):
  PL(d)  = PL0 + 10*n*log10(d/d0) + X_sigma      [dB]  (log-distance + umbra)
  P_rx   = P_tx - PL(d)                          [dBm]
  SNR    = P_rx - P_noise                        [dB]
  loss(SNR) = 1 / (1 + exp(k*(SNR - SNR_mid)))   (sigmoida PER — neteda)
  ms(loss)  = ms0 + alfa * loss/(1-loss)         (aproximatie ARQ: cu cat
              pierzi mai mult, cu atat retransmisiile cresc latenta)
  down      = SNR < snr_down  (sau d > d_max, daca e setat)

Astfel dronele departate de GCS au automat legaturi mai proaste — exact
realitatea SAR si exact unghiul tezei: degradarea devine o consecinta a
geometriei misiunii, masurabila si reproducibila (seed pentru umbra).
"""
import math
import random


class LogDistanceRadioLink:
    def __init__(self,
                 tx_dbm=20.0,        # putere emisie (tipic 100 mW WiFi/teleme)
                 pl0_db=40.0,        # path loss la d0 (2.4 GHz ~ 40 dB la 1 m)
                 d0=1.0,             # distanta de referinta [m]
                 n_exp=2.7,          # exponent (2=spatiu liber, 2.7-3.5 urban)
                 noise_dbm=-90.0,    # prag de zgomot al receptorului
                 shadow_sigma_db=0.0,  # deviatia umbririi log-normale [dB]
                 snr_mid=8.0,        # SNR la care loss=50%
                 k_slope=0.7,        # panta sigmoidei
                 snr_down=0.0,       # sub acest SNR legatura e cazuta
                 ms0=20.0,           # latenta de baza [ms]
                 alpha_ms=60.0,      # crestere latenta cu retransmisiile [ms]
                 jit_frac=0.35,      # jitter = jit_frac * (ms - ms0) + jit0
                 jit0_ms=2.0,
                 d_max=None,         # cutoff dur optional [m]
                 seed=None):
        self.tx_dbm = tx_dbm
        self.pl0_db = pl0_db
        self.d0 = d0
        self.n_exp = n_exp
        self.noise_dbm = noise_dbm
        self.shadow_sigma_db = shadow_sigma_db
        self.snr_mid = snr_mid
        self.k_slope = k_slope
        self.snr_down = snr_down
        self.ms0 = ms0
        self.alpha_ms = alpha_ms
        self.jit_frac = jit_frac
        self.jit0_ms = jit0_ms
        self.d_max = d_max
        self.rng = random.Random(seed)

    # ---- fizica ----
    def path_loss_db(self, d, shadowed=True):
        d = max(float(d), self.d0)
        pl = self.pl0_db + 10.0 * self.n_exp * math.log10(d / self.d0)
        if shadowed and self.shadow_sigma_db > 0.0:
            pl += self.rng.gauss(0.0, self.shadow_sigma_db)
        return pl

    def snr_db(self, d, shadowed=True):
        return self.tx_dbm - self.path_loss_db(d, shadowed) - self.noise_dbm

    # ---- mapari catre parametrii canalului ----
    def loss_from_snr(self, snr):
        x = self.k_slope * (snr - self.snr_mid)
        # sigmoida stabila numeric
        if x >= 0:
            p = 1.0 / (1.0 + math.exp(x))
        else:
            e = math.exp(x)
            p = 1.0 - e / (1.0 + e)
        return min(max(p, 0.0), 0.99)

    def state_for_distance(self, d, shadowed=True):
        """Starea completa a legaturii la distanta d, in schema
        /teleop/linkstate: {ms, jit, loss, down} + diagnostic {snr, rssi, d}."""
        snr = self.snr_db(d, shadowed)
        down = snr < self.snr_down or (self.d_max is not None and d > self.d_max)
        loss = 1.0 if down else self.loss_from_snr(snr)
        ms = self.ms0 + self.alpha_ms * (loss / max(1.0 - loss, 1e-3))
        ms = min(ms, 2000.0)
        jit = self.jit0_ms + self.jit_frac * (ms - self.ms0)
        return {"ms": round(ms, 1), "jit": round(jit, 1),
                "loss": round(loss, 4), "down": bool(down),
                "snr": round(snr, 1),
                "rssi": round(self.tx_dbm - self.path_loss_db(d, False), 1),
                "d": round(float(d), 2)}

    def states_for_positions(self, gcs_xy, positions, shadowed=True):
        """positions: dict id -> (x, y[, z]). Intoarce dict id -> stare."""
        gx, gy = float(gcs_xy[0]), float(gcs_xy[1])
        out = {}
        for did, p in positions.items():
            dx, dy = float(p[0]) - gx, float(p[1]) - gy
            dz = float(p[2]) if len(p) > 2 else 0.0
            d = math.sqrt(dx * dx + dy * dy + dz * dz)
            out[did] = self.state_for_distance(d, shadowed)
        return out


# Profiluri gata calibrate pentru scenarii SAR uzuale.
PROFILES = {
    # camp deschis, telemetrie 2.4 GHz — leg. buna pana ~300 m, moare ~600 m
    "open_field": dict(n_exp=2.4, shadow_sigma_db=2.0, snr_mid=8.0),
    # urban / moloz — atenuare agresiva, util pentru SAR in cladiri prabusite
    "urban_rubble": dict(n_exp=3.3, shadow_sigma_db=5.0, snr_mid=10.0),
    # padure — intre cele doua
    "forest": dict(n_exp=2.9, shadow_sigma_db=4.0, snr_mid=9.0),
}


def make_link(profile="open_field", **overrides):
    cfg = dict(PROFILES.get(profile, {}))
    cfg.update(overrides)
    return LogDistanceRadioLink(**cfg)
