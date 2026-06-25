#!/usr/bin/env python3
"""mission_scenarios.py -- rezultatul de misiune per scenariu (date SIL curate).
Bare = coverage final; eticheta = victime gasite/total; rosu daca s-au ratat victime.
Arata gradatia comms -> rezultat: cu cat scenariul e mai sever, cu atat scade
coverage si, in cazul extrem, se rateaza victime.
Folosire: python3 mission_scenarios.py <dir_cu_sil_summary_json>
Iese: <dir>/fig_mission_scenarios.png
"""
import sys, os, glob, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."

rows = []
for sj in glob.glob(os.path.join(ROOT, "*_summary.json")):
    d = json.load(open(sj))
    name = os.path.basename(sj).replace("_summary.json", "")
    cov = d.get("coverage_final")
    vf = d.get("victims_found")
    vt = d.get("victims_total")
    if cov is None or vf is None:
        continue
    rows.append((name, float(cov), int(vf), int(vt or 5)))

if not rows:
    sys.exit("[!] niciun *_summary.json cu coverage_final/victims_found in " + ROOT)

# sortare dupa coverage descrescator (de la cel mai bun la cel mai sever)
rows.sort(key=lambda r: -r[1])
names = [r[0] for r in rows]
covs  = [r[1] * 100 for r in rows]
vfs   = [r[2] for r in rows]
vts   = [r[3] for r in rows]

OK = "#2c9e4b"; BAD = "#de2d26"
colors = [OK if vf >= vt else BAD for vf, vt in zip(vfs, vts)]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(range(len(rows)), covs, color=colors, alpha=0.85)
for i, (b, vf, vt) in enumerate(zip(bars, vfs, vts)):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.2,
            f"{vf}/{vt}", ha="center", va="bottom", fontsize=10,
            fontweight="bold", color=(BAD if vf < vt else "black"))

ax.set_xticks(range(len(rows)))
ax.set_xticklabels(names, rotation=25, ha="right")
ax.set_ylabel("Acoperire finala [%]")
ax.set_ylim(0, 105)
ax.set_title("Rezultat de misiune per scenariu (date SIL curate)\n"
             "eticheta = victime gasite/total; rosu = victime ratate")
ax.grid(axis="y", alpha=0.3)
ax.legend(handles=[Patch(color=OK, label="toate victimele gasite"),
                   Patch(color=BAD, label="victime ratate")], loc="lower left")
plt.tight_layout()
out = os.path.join(ROOT, "fig_mission_scenarios.png")
plt.savefig(out, dpi=150)
print(f"[ok] {out}")
for n, c, vf, vt in rows:
    print(f"  {n:<18} coverage {c*100:5.1f}%  victime {vf}/{vt}")
