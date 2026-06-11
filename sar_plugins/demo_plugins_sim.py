#!/usr/bin/env python3
"""demo_plugins_sim.py — demonstratia integrata a etajului de misiune.

Ruleaza FARA ROS2 (logica pura) si arata toate plugin-urile cooperand:
  - 5 drone cinematice in lawnmower pe o arie de 120 x 120 m, GCS in (0,0);
  - link radio log-distance (profil urban_rubble): telemetria fiecarei drone
    trece printr-un DegradedChannel a carui stare se recalculeaza din
    distanta — dronele departate pierd mai multe pachete;
  - acoperirea se marcheaza LA GCS doar din telemetria LIVRATA: degradarea
    legaturii se vede direct in metrica de misiune;
  - victimele se detecteaza la bord (pozitia reala) si evenimentele se
    trimit prin acelasi link;
  - bateriile au failsafe RTL/LAND cu prag dinamic dupa distanta de baza.

Produce: demo_trajectories.png, demo_coverage.png,
         demo_loss_vs_distance.png, demo_battery.png
si un bilant numeric cu verificari de sanatate.
"""
import math
import os
import random
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from channel import DegradedChannel
from radio_link import make_link
from coverage import CoverageGrid
from victims import VictimField
from battery import BatteryModel

# ------------------------------ parametri ------------------------------
HALF = 60.0                  # semi-latura ariei [m]
N_DRONES = 5
V = 4.0                      # viteza de croaziera [m/s]
R_SENS = 6.0                 # raza senzorului [m]
LINE_SP = 9.0                # distanta intre liniile lawnmower (1.5 * R)
DT = 0.05
T_MAX = 170.0
TELEM_HZ = 5.0
SEED = 4

rng = random.Random(SEED)

# ------------------------- traseele lawnmower --------------------------
def lawnmower_for_band(y0, y1, x_half):
    wps, y, k = [], y0 + LINE_SP / 2.0, 0
    while y < y1:
        xa, xb = (-x_half, x_half) if k % 2 == 0 else (x_half, -x_half)
        wps += [(xa, y), (xb, y)]
        y += LINE_SP
        k += 1
    return wps

band_h = 2.0 * HALF / N_DRONES
drones = {}
for i in range(N_DRONES):
    did = f"d{i+1}"
    y0 = -HALF + i * band_h
    drones[did] = {
        "x": 0.0, "y": 0.0, "wps": lawnmower_for_band(y0, y0 + band_h, HALF),
        "wp_i": 0, "mode": "MISSION", "traj": [(0.0, 0.0)],
        "bat": BatteryModel(capacity_wh=5.8, p_hover_w=120.0, k_v_w=8.0,
                            soc_rtl=0.15, soc_land=0.05, v_rtl=V,
                            dynamic_margin=1.5),
        "chan": DegradedChannel(seed=SEED + i),
        "sent": 0, "delivered_pairs": [],   # (d_emis, livrat 0/1)
    }

link = make_link("urban_rubble", shadow_sigma_db=2.0, seed=SEED)
grid = CoverageGrid(-HALF, HALF, -HALF, HALF, cell=1.5)
field = VictimField(6, -HALF + 5, HALF - 5, -HALF + 5, HALF - 5,
                    seed=SEED, min_sep=15.0)
cov_t, cov_pct = [], []
soc_hist = {d: [] for d in drones}
ev_sent = ev_delivered = 0

# ------------------------------ simularea ------------------------------
t = 0.0
next_telem = 0.0
next_link_update = 0.0
while t < T_MAX:
    all_done = True
    for did, D in drones.items():
        bat, ch = D["bat"], D["chan"]
        # tinta curenta
        if D["mode"] == "MISSION":
            if D["wp_i"] >= len(D["wps"]):
                D["mode"] = "DONE"
            else:
                tx, ty = D["wps"][D["wp_i"]]
        if D["mode"] == "RTL":
            tx, ty = 0.0, 0.0
        if D["mode"] in ("DONE", "LANDED"):
            tx, ty = D["x"], D["y"]
        # miscare
        dx, dy = tx - D["x"], ty - D["y"]
        dist = math.hypot(dx, dy)
        speed = 0.0
        if D["mode"] in ("MISSION", "RTL") and dist > 1e-6:
            step = min(V * DT, dist)
            D["x"] += dx / dist * step
            D["y"] += dy / dist * step
            speed = step / DT
            if dist <= 0.5:
                if D["mode"] == "MISSION":
                    D["wp_i"] += 1
                elif D["mode"] == "RTL":
                    bat.reached_home(t)
                    D["mode"] = "LANDED"
        D["traj"].append((D["x"], D["y"]))
        # baterie (prag dinamic dupa distanta de baza)
        d_home = math.hypot(D["x"], D["y"])
        prev = bat.state
        st = bat.update(DT, speed=speed, t=t, dist_home=d_home)
        if st != prev:
            if st == BatteryModel.RTL and D["mode"] == "MISSION":
                D["mode"] = "RTL"
                D["t_rtl"] = t
            if st == BatteryModel.LAND:
                D["mode"] = "LANDED"
        if D["mode"] in ("MISSION", "RTL"):
            all_done = False
        # detectie victime la bord -> eveniment prin link
        evs = field.step(t, {did: (D["x"], D["y"])}, R_SENS,
                         p_detect=2.0, dt=DT)
        for ev in evs:
            ev_sent += 1
            if ch.push(t, ("EV", ev)):
                pass
    # actualizarea starii legaturilor din distanta (1 Hz)
    if t >= next_link_update:
        next_link_update = t + 1.0
        for did, D in drones.items():
            d = math.hypot(D["x"], D["y"])
            st = link.state_for_distance(d)
            D["chan"].set_from_dict(st)
            D["_d_now"] = d
    # telemetrie 5 Hz prin link; acoperirea se marcheaza din ce AJUNGE
    if t >= next_telem:
        next_telem = t + 1.0 / TELEM_HZ
        for did, D in drones.items():
            if D["mode"] == "LANDED":
                continue
            D["sent"] += 1
            ok = D["chan"].push(t, ("TM", (D["x"], D["y"])))
            D["delivered_pairs"].append((D.get("_d_now", 0.0), 1 if ok else 0))
    # livrarile ajunse la GCS
    for did, D in drones.items():
        for _td, (kind, payload) in D["chan"].pop_ready(t):
            if kind == "TM":
                grid.mark_disc(payload[0], payload[1], R_SENS, t=t)
            elif kind == "EV":
                ev_delivered += 1
    # esantionare metrici
    if int(t / DT) % int(1.0 / DT) == 0:
        cov_t.append(t)
        cov_pct.append(grid.percent())
        for did, D in drones.items():
            soc_hist[did].append((t, D["bat"].soc()))
    t += DT
    if all_done and field.n_detected == field.n_total:
        pass  # lasam timpul sa curga pt. livrarile in tranzit

# ------------------------------- bilant --------------------------------
print("=== bilant demo ===")
print(f"acoperire finala (la GCS): {grid.percent():.1f}%  "
      f"jaloane: {grid.milestones()}")
print(f"victime: {field.n_detected}/{field.n_total} detectate, "
      f"t_first={field.first_detection_t() and round(field.first_detection_t(),1)} s; "
      f"evenimente livrate {ev_delivered}/{ev_sent}")
ratios = {}
for did, D in drones.items():
    pairs = D["delivered_pairs"]
    far = [ok for d, ok in pairs if d > 50]
    near = [ok for d, ok in pairs if d <= 25]
    ratios[did] = (sum(near) / len(near) if near else 1.0,
                   sum(far) / len(far) if far else 1.0)
    s = D["bat"].summary()
    print(f"  {did}: livrare aproape={ratios[did][0]*100:5.1f}%  "
          f"departe={ratios[did][1]*100:5.1f}%  "
          f"SOC final={s['soc']*100:4.1f}%  stare={s['state']}  "
          f"t_RTL={D.get('t_rtl') and round(D['t_rtl'],1)}")

n_ok = 0
def check(name, cond):
    global n_ok
    print(("[ok]   " if cond else "[FAIL] ") + name)
    n_ok += cond
check("acoperirea la GCS > 70%", grid.percent() > 70.0)
check("toate dronele au declansat failsafe energetic (RTL sau LAND)",
      all(D["bat"].state != "NORMAL" for D in drones.values()))
check("livrarea departe < livrarea aproape (degradare pe distanta)",
      all(f <= a + 1e-9 for a, f in ratios.values())
      and any(f < a - 0.05 for a, f in ratios.values()))
check("victime detectate >= 5/6", field.n_detected >= 5)

# ------------------------------- figuri --------------------------------
OUT = os.path.dirname(os.path.abspath(__file__))
plt.rcParams.update({"font.size": 9})

# 1. traiectorii + victime + acoperire
fig, ax = plt.subplots(figsize=(7.2, 6.6))
ax.imshow(grid.grid, extent=(-HALF, HALF, -HALF, HALF), origin="lower",
          cmap="Greens", alpha=0.30, aspect="equal", vmin=0, vmax=1.6)
for did, D in drones.items():
    xs, ys = zip(*D["traj"])
    ax.plot(xs, ys, lw=1.1, label=did)
    ax.plot(xs[-1], ys[-1], "o", ms=4, color=ax.lines[-1].get_color())
for v in field.positions():
    if v["detected"]:
        ax.plot(v["x"], v["y"], "P", ms=11, mfc="limegreen", mec="k",
                zorder=5)
    else:
        ax.plot(v["x"], v["y"], "X", ms=11, mfc="red", mec="k", zorder=5)
ax.plot(0, 0, "*", ms=16, mfc="gold", mec="k", zorder=6, label="GCS")
ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
ax.set_title("Misiune SAR: traiectorii, acoperire la GCS, victime\n"
             "(P verde = detectata, X rosie = ratata)")
ax.legend(loc="upper right", fontsize=8, ncol=2)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "demo_trajectories.png"),
                                dpi=150); plt.close(fig)

# 2. acoperirea in timp
fig, ax = plt.subplots(figsize=(6.6, 3.6))
ax.plot(cov_t, cov_pct, lw=1.6)
for goal, tg in sorted(grid.milestones().items()):
    ax.axvline(tg, color="gray", ls=":", lw=0.8)
    ax.annotate(f"{goal}%", (tg, 3), rotation=90, fontsize=7, color="gray")
ax.set_xlabel("t [s]"); ax.set_ylabel("acoperire [%]")
ax.set_title("Acoperirea zonei (cunoscuta la GCS, prin link degradat)")
ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "demo_coverage.png"),
                                dpi=150); plt.close(fig)

# 3. pierdere vs distanta: teorie + realizat
fig, ax = plt.subplots(figsize=(6.6, 3.8))
dd = np.linspace(1, 90, 200)
ax.plot(dd, [link.state_for_distance(x, shadowed=False)["loss"] * 100
             for x in dd], "k-", lw=1.5, label="model (fara umbra)")
allp = [p for D in drones.values() for p in D["delivered_pairs"]]
bins = np.arange(0, 95, 5.0)
xs, ys = [], []
for b0, b1 in zip(bins[:-1], bins[1:]):
    sel = [ok for d, ok in allp if b0 <= d < b1]
    if len(sel) >= 20:
        xs.append((b0 + b1) / 2)
        ys.append(100.0 * (1 - sum(sel) / len(sel)))
ax.plot(xs, ys, "o", ms=5, mfc="tab:red", mec="k",
        label="realizat (telemetrie 5 Hz)")
ax.set_xlabel("distanta fata de GCS [m]"); ax.set_ylabel("pierdere [%]")
ax.set_title("Link radio log-distance, profil urban_rubble")
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(os.path.join(OUT,
                                "demo_loss_vs_distance.png"),
                                dpi=150); plt.close(fig)

# 4. bateriile
fig, ax = plt.subplots(figsize=(6.6, 3.8))
for did, hist in soc_hist.items():
    ts, ss = zip(*hist)
    ax.plot(ts, [s * 100 for s in ss], lw=1.4, label=did)
    D = drones[did]
    if D.get("t_rtl") is not None:
        ax.plot(D["t_rtl"],
                dict(hist).get(min(dict(hist),
                                   key=lambda k: abs(k - D["t_rtl"])),
                               0) * 100,
                "v", ms=8, color=ax.lines[-1].get_color())
ax.axhline(15, color="orange", ls="--", lw=0.9)
ax.axhline(5, color="red", ls="--", lw=0.9)
ax.text(1, 16, "prag RTL static", fontsize=7, color="orange")
ax.text(1, 6, "prag LAND", fontsize=7, color="red")
ax.set_xlabel("t [s]"); ax.set_ylabel("SOC [%]")
ax.set_title("Bateriile dronelor (triunghi = momentul RTL)")
ax.legend(fontsize=8, ncol=3); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "demo_battery.png"),
                                dpi=150); plt.close(fig)

print(f"\n[ok] 4 figuri scrise in {OUT}")
sys.exit(0 if n_ok == 4 else 1)
