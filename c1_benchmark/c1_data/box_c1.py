#!/usr/bin/env python3
"""box_c1.py -- box-plot p95 per conditie, CycloneDDS vs Zenoh (N repetitii).
Vizualizeaza imprastierea: DDS = cutii mici/stranse, Zenoh = cutii inalte/imprastiate.
Folosire: python3 box_c1.py <dir_campanie> [REF_payload]
Iese: <dir>/analysis/fig_boxplot_p95.png
"""
import sys, os, glob, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
REF = int(sys.argv[2]) if len(sys.argv) > 2 else 4096

COND_ORDER = ["loss_20", "loss_25", "loss_30"]
RMW_ORDER = ["cyclonedds", "zenoh"]
LABELS = {"cyclonedds": "CycloneDDS", "zenoh": "Zenoh"}
COLORS = {"cyclonedds": "#2c7fb8", "zenoh": "#de2d26"}

def collect(rmw, cond):
    vals = []
    for sj in glob.glob(os.path.join(ROOT, rmw, cond, "rep*",
                                     f"transport_p{REF}_summary.json")):
        d = json.load(open(sj))
        if d.get("p95_ms") is not None:
            vals.append(d["p95_ms"])
    return vals

# ce conditii sunt prezente (pe axa de pierdere)
conds = [c for c in COND_ORDER if any(collect(r, c) for r in RMW_ORDER)]
if not conds:
    sys.exit(f"[!] nicio conditie loss_* cu date la REF={REF}")

ns = {(r, c): len(collect(r, c)) for r in RMW_ORDER for c in conds}

fig, ax = plt.subplots(figsize=(8, 5))
width = 0.36
pos = list(range(len(conds)))
for i, rmw in enumerate(RMW_ORDER):
    data = [collect(rmw, c) for c in conds]
    offs = [p + (i - 0.5) * width for p in pos]
    bp = ax.boxplot(data, positions=offs, widths=width * 0.9,
                    patch_artist=True, showfliers=True,
                    medianprops=dict(color="black", linewidth=1.4),
                    flierprops=dict(marker="o", markersize=3, alpha=0.5))
    for box in bp["boxes"]:
        box.set(facecolor=COLORS[rmw], alpha=0.75)
    ax.plot([], [], color=COLORS[rmw], linewidth=9, alpha=0.75,
            label=LABELS[rmw])

ax.set_xticks(pos)
ax.set_xticklabels([c.replace("loss_", "") + "%" for c in conds])
ax.set_xlabel("Pierdere pachete")
ax.set_ylabel("RTT p95 [ms]")
ax.set_title("Latenta de coada (p95) per conditie -- CycloneDDS vs Zenoh (N=10)")
ax.legend(loc="upper left")
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()

out = os.path.join(ROOT, "analysis", "fig_boxplot_p95.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
plt.savefig(out, dpi=150)
print(f"[ok] {out}")
print("N per (rmw, conditie):", {f"{r}/{c}": ns[(r, c)]
                                 for r in RMW_ORDER for c in conds})
