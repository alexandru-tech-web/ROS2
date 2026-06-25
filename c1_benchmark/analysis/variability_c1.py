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
allns = sorted({cv(data.get(r, {}).get(c, []))[1] for r in rmws for c in conds
                if data.get(r, {}).get(c)})
nlabel = str(allns[0]) if len(allns) == 1 else f"{allns[0]}..{allns[-1]}"

fig, ax = plt.subplots(figsize=(11, 5.4))
for i, r in enumerate(rmws):
    cvs, nns = [], []
    for c in conds:
        v, n = cv(data.get(r, {}).get(c, []))
        cvs.append(v); nns.append(n)
    pos = [xi + i*w for xi in x]
    bars = ax.bar(pos, cvs, w, label=r, color=COL.get(r, None),
                  edgecolor="black", linewidth=0.5, alpha=0.95)
    for b, v in zip(bars, cvs):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+1, f"{v:.0f}%",
                ha="center", va="bottom", fontsize=8)

ax.axhline(20, ls="--", color="gray", lw=1)
ax.text(len(conds)-0.5, 22, "prag predictibilitate ~20%", fontsize=8,
        color="gray", ha="right")
ax.set_xticks([xi + w*(len(rmws)-1)/2 for xi in x])
ax.set_xticklabels(conds, rotation=20, ha="right", fontsize=10)
ax.set_xlabel("conditie de retea (tc netem)", fontsize=11)
ax.set_ylabel("coeficient de variatie al p95 [%]", fontsize=11)
ax.set_title("Predictibilitatea latentei de coada (date curate)\n"
             "jos = predictibil; sus = imprevizibil de la o rulare la alta", fontsize=12)
ax.legend(title="RMW", fontsize=10)
ax.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.6); ax.set_axisbelow(True)
fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.22)
fig.text(0.5, 0.02, f"SIL (loopback); N={nlabel} repetitii; sarcina utila 4096 B; "
         "CV = abaterea standard / media a p95 pe repetitii.",
         ha="center", va="bottom", fontsize=8.5)
out_dir = os.path.join(ROOT, "analysis"); os.makedirs(out_dir, exist_ok=True)
for ext in ("png", "pdf"):
    plt.savefig(os.path.join(out_dir, f"fig_variability_c1.{ext}"), dpi=200)
print("[ok]", os.path.join(out_dir, "fig_variability_c1") + ".{png,pdf}")
for r in rmws:
    for c in conds:
        v, n = cv(data.get(r, {}).get(c, []))
        print(f"  {r:<12} {c:<14} CV={v:5.0f}%  N={n}")
