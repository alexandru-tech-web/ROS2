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
COLORS = {"cyclonedds": "#1f77b4", "zenoh": "#9467bd"}

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

nvals = sorted(set(ns.values()))
nlabel = str(nvals[0]) if len(nvals) == 1 else f"{nvals[0]}..{nvals[-1]}"

ax.set_xticks(pos)
ax.set_xticklabels([c.replace("loss_", "") + "%" for c in conds], fontsize=10)
ax.set_xlabel("pierdere de pachete (tc netem)", fontsize=11)
ax.set_ylabel("RTT p95 [ms]", fontsize=11)
ax.set_title("Latenta de coada (p95) per conditie -- CycloneDDS vs Zenoh", fontsize=12)
ax.legend(loc="upper left", fontsize=10)
ax.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.6)
ax.set_axisbelow(True)
fig.subplots_adjust(left=0.10, right=0.97, top=0.91, bottom=0.20)
fig.text(0.5, 0.02, f"SIL (loopback); N={nlabel} repetitii; sarcina utila {REF} B; "
         "fiecare cutie = distributia p95 pe repetitii.",
         ha="center", va="bottom", fontsize=8.5)

od = os.path.join(ROOT, "analysis")
os.makedirs(od, exist_ok=True)
for ext in ("png", "pdf"):
    plt.savefig(os.path.join(od, "fig_boxplot_p95." + ext), dpi=200)
print(f"[ok] {os.path.join(od, 'fig_boxplot_p95')}.{{png,pdf}}")
print("N per (rmw, conditie):", {f"{r}/{c}": ns[(r, c)]
                                 for r in RMW_ORDER for c in conds})
