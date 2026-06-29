#!/usr/bin/env python3
"""date_sar.py -- UN generator de date, samanta din numerele campaniilor mele reale.

ONESTITATE (vezi CLAUDE.md sec.0 si fiecare teorie.md care le foloseste): datele
produse aici sunt SINTETICE. Sunt insa CALIBRATE pe numerele reale din campania C1
(p95 RTT [ms] si pierdere [%] pentru rmw_cyclonedds_cpp 'DDS' vs rmw_zenoh_cpp
'Zenoh', sub tc netem, N=5) si pe modelul de canal log-distanta din campania M.
Nu inlocuiesc datele reale -- servesc invatarii (semnal realist, reproductibil).

Tot ce e aleator trece prin numpy.random.default_rng(seed) -> determinist.
Fiecare functie returneaza un pandas.DataFrame si are un _selftest pe forme,
absenta NaN si rata de pierdere in toleranta.

Ruleaza verificarile: python3 date_sar.py   (iesire 0 = PASS, non-0 = FAIL).
"""
import sys

import numpy as np
import pandas as pd

Z95 = 1.6448536269514722  # cuantila 0.95 a normalei standard

# Tabelul C1 real (samanta). Cheie -> (p95_DDS_ms, p95_Zenoh_ms, loss_DDS, loss_Zenoh).
# Sursa: campania C1 (degradare uniforma cu tc netem, N=5). Randul 'ideal' (fara
# degradare, loopback) e baza de RTT mic; restul sunt din masuratori.
C1_TABLE = {
    "ideal":        (12.0,   20.0,   0.00, 0.00),
    "loss_5":       (146.0,  172.0,  0.00, 0.04),
    "loss_15":      (1056.0, 690.0,  0.01, 0.02),
    "loss_30":      (2320.0, 3645.0, 0.39, 0.35),
    "lat200_jit50": (490.0,  477.0,  0.02, 0.01),
    "lat200_l15":   (2523.0, 4125.0, 0.34, 0.22),
}
CONDITIONS = list(C1_TABLE)
MIDDLEWARES = ("DDS", "Zenoh")


def _cond_params(cond, mw):
    """(p95_target_ms, loss_rate) pentru o conditie si un middleware."""
    p95_dds, p95_zen, loss_dds, loss_zen = C1_TABLE[cond]
    if mw == "DDS":
        return p95_dds, loss_dds
    return p95_zen, loss_zen


def _base_latency_ms(cond):
    """Latenta de baza injectata de netem (feature), dedusa din numele conditiei."""
    if cond.startswith("lat200"):
        return 200.0
    return 1.0  # loopback: ~sub-milisecunda, rotunjit la 1 ms


def _jitter_ms(cond):
    """Jitterul nominal injectat (feature)."""
    if "jit50" in cond:
        return 50.0
    return 2.0


# ----------------------------------------------------------------------------
def make_latency_dataset(n_per_cond=200, seed=0):
    """Per-pachet: latente lognormale calibrate sa dea p95-ul din C1_TABLE, plus
    pierderi Bernoulli cu rata din tabel, pentru fiecare (conditie, middleware).

    Coloane: condition, middleware, loss_pct, base_lat_ms, jitter_ms, distance_m,
    rtt_ms (tinta de regresie), dropped {0,1}.
    """
    g = np.random.default_rng(seed)
    rows = []
    for cond in CONDITIONS:
        for mw in MIDDLEWARES:
            p95_target, loss_rate = _cond_params(cond, mw)
            base = _base_latency_ms(cond)
            jit = _jitter_ms(cond)
            # imprastiere mai mare cand pierderea e mare (cozi lungi reale)
            sigma = 0.30 + 0.9 * loss_rate
            distance = g.uniform(5.0, 60.0, size=n_per_cond)
            dist_mult = 1.0 + 0.0015 * distance          # efect de distanta ~ pana la 9%
            # centram lognormalul ca p95-ul EMPIRIC (dupa dist_mult) sa fie ~ tinta
            mu = np.log(p95_target / 1.05) - sigma * Z95
            core = np.exp(mu + sigma * g.standard_normal(size=n_per_cond))
            rtt = core * dist_mult
            dropped = (g.random(size=n_per_cond) < loss_rate).astype(int)
            for k in range(n_per_cond):
                rows.append(dict(
                    condition=cond, middleware=mw,
                    loss_pct=round(loss_rate * 100.0 + g.normal(0, 0.3), 3),
                    base_lat_ms=base, jitter_ms=jit,
                    distance_m=round(float(distance[k]), 2),
                    rtt_ms=round(float(rtt[k]), 3),
                    dropped=int(dropped[k]),
                ))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
def make_link_usability_dataset(n_per_cond=120, seed=1,
                                lat_thresh_ms=300.0, loss_thresh=0.05):
    """Ferestre de link rezumate -> eticheta binara `usable`.

    Pragurile sunt motivate pentru teleoperatie in timp real (documentate in
    M08/M09): bucla de teleoperatie se degradeaza peste ~300 ms RTT dus-intors,
    deci o legatura e utila daca p95 RTT < lat_thresh_ms SI pierderea < loss_thresh.
    Cu acest prag, conditiile lat200_* si loss_15/30 cad pe 'inutilizabil', iar
    clasa 'usable' ramane minoritara (~30%) -- dezechilibrul real, util la M09.
    Clasele ies DEZECHILIBRATE -- exact cazul real (degradarea face majoritatea
    ferestrelor inutilizabile), util la M09.

    Coloane: condition, middleware, p95_ms, loss_frac, jitter_ms, base_lat_ms,
    mw_zenoh {0,1}, distance_m, usable {0,1}.
    """
    g = np.random.default_rng(seed)
    rows = []
    for cond in CONDITIONS:
        for mw in MIDDLEWARES:
            p95_target, loss_rate = _cond_params(cond, mw)
            base, jit = _base_latency_ms(cond), _jitter_ms(cond)
            # fiecare fereastra: p95 in jurul tintei (zgomot multiplicativ) + loss zgomotos
            p95 = p95_target * np.exp(g.normal(0, 0.20, size=n_per_cond))
            loss = np.clip(loss_rate + g.normal(0, 0.02, size=n_per_cond), 0.0, 1.0)
            distance = g.uniform(5.0, 60.0, size=n_per_cond)
            usable = ((p95 < lat_thresh_ms) & (loss < loss_thresh)).astype(int)
            for k in range(n_per_cond):
                rows.append(dict(
                    condition=cond, middleware=mw,
                    p95_ms=round(float(p95[k]), 3),
                    loss_frac=round(float(loss[k]), 4),
                    jitter_ms=jit, base_lat_ms=base,
                    mw_zenoh=1 if mw == "Zenoh" else 0,
                    distance_m=round(float(distance[k]), 2),
                    usable=int(usable[k]),
                ))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
_CHANNEL_PROFILES = {
    "open_field":   dict(n_exp=2.2, shadow_db=3.0),
    "urban_rubble": dict(n_exp=3.5, shadow_db=6.0),
}


def make_channel_dataset(profile="urban_rubble", seed=2, n=400,
                         pl0_db=40.0, d0_m=1.0, tx_dbm=20.0, sens_dbm=-90.0):
    """Model log-distanta (campania M): PL(d)=PL0 + 10*n*log10(d/d0) + umbrire.

    profile in {open_field (n mic), urban_rubble (n mare)}. Mapeaza puterea
    receptionata pe o fractie de telemetrie livrata (sigmoida pe marja fata de
    sensibilitate). Coloane: profile, distance_m, path_loss_db, rx_dbm,
    margin_db, delivered_frac.
    """
    if profile not in _CHANNEL_PROFILES:
        raise ValueError("profil necunoscut: %r (open_field|urban_rubble)" % (profile,))
    p = _CHANNEL_PROFILES[profile]
    g = np.random.default_rng(seed)
    distance = g.uniform(d0_m, 80.0, size=n)
    shadow = g.normal(0.0, p["shadow_db"], size=n)
    path_loss = pl0_db + 10.0 * p["n_exp"] * np.log10(distance / d0_m) + shadow
    rx = tx_dbm - path_loss
    margin = rx - sens_dbm
    delivered = 1.0 / (1.0 + np.exp(-0.35 * margin))   # sigmoida pe marja [dB]
    return pd.DataFrame(dict(
        profile=profile,
        distance_m=np.round(distance, 2),
        path_loss_db=np.round(path_loss, 2),
        rx_dbm=np.round(rx, 2),
        margin_db=np.round(margin, 2),
        delivered_frac=np.round(delivered, 4),
    ))


# ----------------------------------------------------------------------------
def make_mission_outcome_dataset(n=500, seed=3):
    """Tinta binara mission_complete ca functie zgomotoasa de fractia livrata
    (si de latenta/numarul de drone). Pentru arbori/ensembluri (M12-M13).

    Coloane: delivered_frac, p95_ms, n_drones, mission_complete {0,1}.
    """
    g = np.random.default_rng(seed)
    delivered = g.uniform(0.2, 1.0, size=n)
    p95 = g.uniform(10.0, 4000.0, size=n)
    n_drones = g.integers(2, 6, size=n)
    # succesul creste cu livrarea, scade cu latenta mare; prag in jur de 0.6 livrare
    logit = 6.0 * (delivered - 0.6) - 0.0008 * (p95 - 500.0) + 0.2 * (n_drones - 4)
    prob = 1.0 / (1.0 + np.exp(-logit))
    complete = (g.random(size=n) < prob).astype(int)
    return pd.DataFrame(dict(
        delivered_frac=np.round(delivered, 4),
        p95_ms=np.round(p95, 1),
        n_drones=n_drones.astype(int),
        mission_complete=complete.astype(int),
    ))


# ----------------------------------------------------------------------------
def make_latency_series(cond="loss_15", length=300, seed=4, middleware="DDS"):
    """Serie temporala AR(1) de RTT cu spike-uri la evenimente de pierdere
    (pentru serii temporale / retele, M19-M20).

    Coloane: t, rtt_ms, dropped {0,1}. Media seriei urmareste p95-ul conditiei.
    """
    if cond not in C1_TABLE:
        raise ValueError("conditie necunoscuta: %r" % (cond,))
    p95_target, loss_rate = _cond_params(cond, middleware)
    g = np.random.default_rng(seed)
    phi = 0.6                          # persistenta AR(1)
    level = p95_target / 1.5           # nivel mediu sub p95
    x = level
    t = np.arange(length)
    rtt = np.empty(length)
    dropped = np.zeros(length, dtype=int)
    for i in range(length):
        x = level + phi * (x - level) + g.normal(0, 0.10 * level)
        if g.random() < loss_rate:     # spike + marcaj de pierdere la evenimente
            x += g.uniform(0.5, 2.0) * level
            dropped[i] = 1
        rtt[i] = max(0.1, x)
    return pd.DataFrame(dict(t=t, rtt_ms=np.round(rtt, 3), dropped=dropped))


# ----------------------------------------------------------------------------
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # ---- make_latency_dataset
    df = make_latency_dataset(n_per_cond=400, seed=0)
    ck("latency: forme (6 cond x 2 mw x 400)", len(df) == 6 * 2 * 400)
    ck("latency: fara NaN", not df.isnull().values.any())
    ck("latency: coloane asteptate",
       set(["condition", "middleware", "loss_pct", "base_lat_ms", "jitter_ms",
            "distance_m", "rtt_ms", "dropped"]).issubset(df.columns))
    # p95 empiric ~ tinta (toleranta 25%) pe un caz degradat si pe ideal
    sub = df[(df.condition == "loss_30") & (df.middleware == "Zenoh")]
    p95_emp = np.percentile(sub.rtt_ms, 95)
    ck("latency: p95 loss_30/Zenoh ~ 3645 ms (+-25%)", abs(p95_emp - 3645.0) / 3645.0 < 0.25)
    sub2 = df[(df.condition == "ideal") & (df.middleware == "DDS")]
    ck("latency: p95 ideal/DDS ~ 12 ms (+-30%)",
       abs(np.percentile(sub2.rtt_ms, 95) - 12.0) / 12.0 < 0.30)
    # rata de pierdere empirica ~ tabel (loss_30/DDS = 0.39)
    sub3 = df[(df.condition == "loss_30") & (df.middleware == "DDS")]
    ck("latency: rata dropped loss_30/DDS ~ 0.39 (+-0.06)", abs(sub3.dropped.mean() - 0.39) < 0.06)

    # ---- make_link_usability_dataset (dezechilibru)
    du = make_link_usability_dataset(n_per_cond=200, seed=1)
    ck("usability: fara NaN si eticheta binara", not du.isnull().values.any()
       and set(du.usable.unique()).issubset({0, 1}))
    frac_usable = du.usable.mean()
    ck("usability: clase DEZECHILIBRATE (usable < 40%)", frac_usable < 0.40)
    # ideal/DDS trebuie sa fie majoritar usable; loss_30 majoritar inutilizabil
    ck("usability: ideal mai des usable decat loss_30",
       du[du.condition == "ideal"].usable.mean() > du[du.condition == "loss_30"].usable.mean())

    # ---- make_channel_dataset (log-distanta)
    dc_open = make_channel_dataset("open_field", seed=2, n=400)
    dc_urb = make_channel_dataset("urban_rubble", seed=2, n=400)
    ck("channel: fara NaN, delivered in [0,1]",
       not dc_urb.isnull().values.any() and dc_urb.delivered_frac.between(0, 1).all())
    ck("channel: path loss creste cu distanta (corelatie > 0.8)",
       np.corrcoef(dc_urb.distance_m, dc_urb.path_loss_db)[0, 1] > 0.8)
    ck("channel: urban (n mare) livreaza in medie mai putin decat open_field",
       dc_urb.delivered_frac.mean() < dc_open.delivered_frac.mean())

    # ---- make_mission_outcome_dataset
    dm = make_mission_outcome_dataset(n=600, seed=3)
    ck("mission: fara NaN, eticheta binara", not dm.isnull().values.any()
       and set(dm.mission_complete.unique()).issubset({0, 1}))
    hi = dm[dm.delivered_frac > 0.8].mission_complete.mean()
    lo = dm[dm.delivered_frac < 0.4].mission_complete.mean()
    ck("mission: succes mai mare la livrare mare decat la livrare mica", hi > lo)

    # ---- make_latency_series
    ds = make_latency_series("loss_15", length=400, seed=4)
    ck("series: lungime si fara NaN", len(ds) == 400 and not ds.isnull().values.any())
    ck("series: exista cel putin un spike marcat (dropped)", ds.dropped.sum() >= 1)
    ck("series: determinist la aceeasi samanta",
       make_latency_series("loss_15", length=50, seed=4).rtt_ms.equals(
           make_latency_series("loss_15", length=50, seed=4).rtt_ms))

    print("\nTOATE VERIFICARILE date_sar AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
