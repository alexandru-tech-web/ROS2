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
nset = sorted({len(data.get(r, {}).get(c, [])) for r in rmws for c in conds
               if data.get(r, {}).get(c)})
nlabel = str(nset[0]) if len(nset) == 1 else f"{nset[0]}..{nset[-1]}"

random.seed(0)
fig, ax = plt.subplots(figsize=(11, 5.5))
for i, r in enumerate(rmws):
    off = (i - (len(rmws)-1)/2)*0.18
    for j, c in enumerate(conds):
        vals = data.get(r, {}).get(c, [])
        xs = [j+off+random.uniform(-0.05, 0.05) for _ in vals]
        ax.scatter(xs, vals, s=28, color=COL.get(r), alpha=0.7,
                   edgecolors="white", linewidths=0.5, zorder=3)
ax.set_xticks(range(len(conds)))
ax.set_xticklabels(conds, rotation=20, ha="right", fontsize=10)
ax.set_xlabel("conditie de retea (tc netem)", fontsize=11)
ax.set_ylabel("RTT p95 [ms] (sarcina utila 4096 B)", fontsize=11)
ax.set_title("Dispersia repetitiilor per conditie (date curate)\n"
             "CycloneDDS grupat (predictibil) vs Zenoh imprastiat (imprevizibil)", fontsize=12)
ax.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.6); ax.set_axisbelow(True)
ax.legend(handles=[Patch(color=COL[r], label=r) for r in rmws], title="RMW", fontsize=10)
fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.22)
fig.text(0.5, 0.02, f"SIL (loopback); N={nlabel} repetitii; sarcina utila 4096 B; "
         "fiecare punct = o repetitie.", ha="center", va="bottom", fontsize=8.5)
od = os.path.join(ROOT, "analysis"); os.makedirs(od, exist_ok=True)
for ext in ("png", "pdf"):
    plt.savefig(os.path.join(od, f"fig_strip_p95.{ext}"), dpi=200)
print("[ok]", os.path.join(od, "fig_strip_p95") + ".{png,pdf}")
