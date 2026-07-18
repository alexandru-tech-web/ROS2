#!/usr/bin/env python3
"""mission_c1.py -- rata de succes a misiunii per conditie, CycloneDDS vs Zenoh.
Succes = run-ul atinge coverage>=0.95 SI victims_found>=5 (altfel esec).
Aceeasi logica ca bench_core.mission_done_time, ca sa fie consistent cu analyze.
Folosire: python3 mission_c1.py <dir_campanie>
Iese: <dir>/analysis/fig_mission_success.png
"""
import sys, os, glob, csv, io
import sys as _sys; csv.field_size_limit(min(_sys.maxsize, 2**31 - 1))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
COND_ORDER = ["loss_20", "loss_25", "loss_30"]
RMW_ORDER = ["cyclonedds", "zenoh"]
LABELS = {"cyclonedds": "CycloneDDS", "zenoh": "Zenoh"}
COLORS = {"cyclonedds": "#2c7fb8", "zenoh": "#de2d26"}
VICTIMS_TOTAL, COVERAGE_GOAL = 5, 0.95

def mission_done(txt):
    rdr = csv.DictReader(io.StringIO(txt))
    for row in rdr:
        try:
            if (float(row["coverage"]) >= COVERAGE_GOAL
                    and int(row["victims_found"]) >= VICTIMS_TOTAL):
                return float(row["t_s"])
        except (KeyError, ValueError):
            return None
    return None

def rate(rmw, cond):
    succ = tot = 0
    for mm in glob.glob(os.path.join(ROOT, rmw, cond, "rep*", "mission_metrics.csv")):
        tot += 1
        if mission_done(open(mm).read()) is not None:
            succ += 1
    return succ, tot

conds = [c for c in COND_ORDER if any(rate(r, c)[1] for r in RMW_ORDER)]
if not conds:
    sys.exit("[!] niciun mission_metrics.csv pe conditiile loss_*")

fig, ax = plt.subplots(figsize=(8, 5))
width = 0.36
pos = list(range(len(conds)))
for i, rmw in enumerate(RMW_ORDER):
    fracs, ntot = [], []
    for c in conds:
        s, t = rate(rmw, c)
        fracs.append(100.0 * s / t if t else 0.0)
        ntot.append(f"{s}/{t}")
    offs = [p + (i - 0.5) * width for p in pos]
    bars = ax.bar(offs, fracs, width=width * 0.9, color=COLORS[rmw],
                  alpha=0.85, label=LABELS[rmw])
    for b, lab in zip(bars, ntot):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, lab,
                ha="center", va="bottom", fontsize=8)

ax.set_xticks(pos)
ax.set_xticklabels([c.replace("loss_", "") + "%" for c in conds])
ax.set_xlabel("Pierdere pachete")
ax.set_ylabel("Succes misiune [%]")
ax.set_ylim(0, 109)
ax.set_title("Rata de succes a misiunii per conditie -- CycloneDDS vs Zenoh")
ax.legend(loc="lower left")
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
out = os.path.join(ROOT, "analysis", "fig_mission_success.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
plt.savefig(out, dpi=150)
print(f"[ok] {out}")
for r in RMW_ORDER:
    print(r, {c: f"{rate(r,c)[0]}/{rate(r,c)[1]}" for c in conds})
