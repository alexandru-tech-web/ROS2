#!/usr/bin/env python3
"""variability_c1.py -- arata VIZUAL predictibilitatea transportului:
coeficientul de variatie (CV = std/medie a p95 peste repetitii) per conditie,
pentru fiecare RMW. DDS jos (predictibil), Zenoh sus (imprevizibil).
Complement la fig_transport (care arata magnitudinea); asta arata predictibilitatea.
Folosire: python3 variability_c1.py <dir_campanie>
Iese: <dir>/analysis/fig_variability_c1.png
"""
import sys, os, glob, json, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
PAYLOAD = "4096"
ORDER = ["loss_5","loss_15","loss_20","loss_25","loss_30","lat200_jit50","lat200_l15"]

# colecteaza p95 pe repetitii: data[rmw][cond] = [p95,...]
data = {}
for sj in glob.glob(os.path.join(ROOT, "*", "*", "rep*",
                                  f"transport_p{PAYLOAD}_summary.json")):
    parts = sj.split(os.sep)
    rmw, cond = parts[-4], parts[-3]
    try:
        d = json.load(open(sj))
    except Exception:
        continue
    data.setdefault(rmw, {}).setdefault(cond, []).append(d.get("p95_ms"))

if not data:
    sys.exit("[!] niciun transport_p%s_summary.json sub %s" % (PAYLOAD, ROOT))

def cv(vals):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2: return 0.0, len(vals)
    m = sum(vals)/len(vals)
    if m == 0: return 0.0, len(vals)
    var = sum((v-m)**2 for v in vals)/(len(vals)-1)
    return 100.0*math.sqrt(var)/m, len(vals)

rmws = sorted(data.keys())
# pastreaza doar conditiile cu magnitudine relevanta (medie p95 > 300ms la vreun RMW)
conds = []
for c in ORDER:
    means = []
    for r in rmws:
        vv = [v for v in data.get(r, {}).get(c, []) if v is not None]
        if vv: means.append(sum(vv)/len(vv))
    if means and max(means) > 300:
        conds.append(c)
if not conds:
    conds = [c for c in ORDER if any(c in data.get(r, {}) for r in rmws)]

COL = {"cyclonedds": "#1f77b4", "zenoh": "#9467bd"}
x = range(len(conds))
w = 0.8/len(rmws)
fig, ax = plt.subplots(figsize=(11, 5))
for i, r in enumerate(rmws):
    cvs, ns = [], []
    for c in conds:
        v, n = cv(data.get(r, {}).get(c, []))
        cvs.append(v); ns.append(n)
    pos = [xi + i*w for xi in x]
    bars = ax.bar(pos, cvs, w, label=r, color=COL.get(r, None), alpha=0.9)
    for b, v in zip(bars, cvs):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+1, f"{v:.0f}%",
                ha="center", va="bottom", fontsize=8)

ax.axhline(20, ls="--", color="gray", lw=1)
ax.text(len(conds)-0.5, 22, "prag predictibilitate ~20%", fontsize=8,
        color="gray", ha="right")
ax.set_xticks([xi + w*(len(rmws)-1)/2 for xi in x])
ax.set_xticklabels(conds, rotation=20, ha="right")
ax.set_ylabel("Coeficient de variatie al p95 [%]  (std/medie peste repetitii)")
ax.set_title("Predictibilitatea latentei de coada (date curate, N=10)\n"
             "jos = predictibil; sus = imprevizibil de la o rulare la alta")
ax.legend(title="RMW")
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
out_dir = os.path.join(ROOT, "analysis"); os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "fig_variability_c1.png")
plt.savefig(out, dpi=150); print("[ok]", out)
for r in rmws:
    for c in conds:
        v, n = cv(data.get(r, {}).get(c, []))
        print(f"  {r:<12} {c:<14} CV={v:5.0f}%  N={n}")
