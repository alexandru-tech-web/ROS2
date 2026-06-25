#!/usr/bin/env python3
"""payload_c1.py -- p95 mediu vs marimea payload-ului (64/4096/65536 B), per RMW,
pentru o conditie data. Arata cum scaleaza fiecare middleware cu marimea mesajului.
Folosire: python3 payload_c1.py <dir_campanie> [conditie=loss_30]
Iese: <dir>/analysis/fig_payload_<conditie>.png
"""
import sys, os, glob, json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
COND = sys.argv[2] if len(sys.argv) > 2 else "loss_30"
PAYLOADS = [64, 4096, 65536]
COL = {"cyclonedds": "#1f77b4", "zenoh": "#9467bd"}

# data[rmw][payload] = [p95,...]
data = {}
for pl in PAYLOADS:
    for sj in glob.glob(os.path.join(ROOT,"*",COND,"rep*",f"transport_p{pl}_summary.json")):
        rmw = sj.split(os.sep)[-4]
        try: v = json.load(open(sj)).get("p95_ms")
        except Exception: continue
        if v is not None: data.setdefault(rmw,{}).setdefault(pl,[]).append(v)
if not data: sys.exit(f"[!] niciun summary pentru conditia {COND} sub {ROOT}")

nset = sorted({len(v) for d in data.values() for v in d.values()})
nlabel = str(nset[0]) if len(nset) == 1 else f"{nset[0]}..{nset[-1]}"

fig, ax = plt.subplots(figsize=(9, 5.5))
for r in sorted(data.keys()):
    xs, ys = [], []
    for pl in PAYLOADS:
        vv = data.get(r, {}).get(pl, [])
        if vv: xs.append(pl); ys.append(sum(vv)/len(vv))
    ax.plot(xs, ys, "o-", color=COL.get(r), label=r, lw=2, ms=8)
ax.set_xscale("log"); ax.set_xticks(PAYLOADS)
ax.get_xaxis().set_major_formatter(plt.matplotlib.ticker.ScalarFormatter())
ax.set_xlabel("sarcina utila [B] (scara log)", fontsize=11)
ax.set_ylabel("RTT p95 mediu [ms]", fontsize=11)
ax.set_title(f"Scalarea cu marimea mesajului -- conditia '{COND}'", fontsize=12)
ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6); ax.set_axisbelow(True)
ax.legend(title="RMW", fontsize=10)
fig.subplots_adjust(left=0.09, right=0.97, top=0.92, bottom=0.18)
fig.text(0.5, 0.02, f"SIL (loopback); N={nlabel} repetitii; conditia '{COND}'; "
         "medie p95 pe repetitii.", ha="center", va="bottom", fontsize=8.5)
od = os.path.join(ROOT, "analysis"); os.makedirs(od, exist_ok=True)
for ext in ("png", "pdf"):
    plt.savefig(os.path.join(od, f"fig_payload_{COND}.{ext}"), dpi=200)
print("[ok]", os.path.join(od, f"fig_payload_{COND}") + ".{png,pdf}")
