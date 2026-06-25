#!/usr/bin/env python3
"""strip_c1.py -- punctele individuale p95 ale celor N repetitii, per conditie.
Arata imprevizibilitatea pe DATE BRUTE: DDS grupat strans, Zenoh imprastiat.
Folosire: python3 strip_c1.py <dir_campanie>
Iese: <dir>/analysis/fig_strip_p95.png
"""
import sys, os, glob, json, random
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
ORDER = ["loss_15","loss_20","loss_25","loss_30","lat200_jit50","lat200_l15"]
COL = {"cyclonedds": "#1f77b4", "zenoh": "#9467bd"}

data = {}
for sj in glob.glob(os.path.join(ROOT,"*","*","rep*","transport_p4096_summary.json")):
    p = sj.split(os.sep); rmw, cond = p[-4], p[-3]
    try: v = json.load(open(sj)).get("p95_ms")
    except Exception: continue
    if v is not None: data.setdefault(rmw,{}).setdefault(cond,[]).append(v)
if not data: sys.exit("[!] niciun summary sub "+ROOT)

rmws = sorted(data.keys())
conds = [c for c in ORDER if any(c in data.get(r,{}) for r in rmws)]
random.seed(0)
fig, ax = plt.subplots(figsize=(11,5.5))
for i, r in enumerate(rmws):
    off = (i - (len(rmws)-1)/2)*0.18
    for j, c in enumerate(conds):
        vals = data.get(r,{}).get(c,[])
        xs = [j+off+random.uniform(-0.05,0.05) for _ in vals]
        ax.scatter(xs, vals, s=28, color=COL.get(r), alpha=0.7,
                   edgecolors="white", linewidths=0.5, zorder=3)
ax.set_xticks(range(len(conds))); ax.set_xticklabels(conds, rotation=20, ha="right")
ax.set_ylabel("p95 RTT [ms] (payload 4096) -- fiecare punct = o repetitie")
ax.set_title("Dispersia repetitiilor (date curate, N=10)\n"
             "DDS grupat (predictibil) vs Zenoh imprastiat (imprevizibil)")
ax.grid(axis="y", alpha=0.3)
ax.legend(handles=[Patch(color=COL[r], label=r) for r in rmws], title="RMW")
plt.tight_layout()
od = os.path.join(ROOT,"analysis"); os.makedirs(od, exist_ok=True)
out = os.path.join(od,"fig_strip_p95.png"); plt.savefig(out, dpi=150); print("[ok]", out)
