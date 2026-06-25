#!/usr/bin/env python3
"""cdf_c1.py -- CDF empirica a RTT-urilor brute, per RMW, pentru o conditie.
Citeste fisierele transport_p<payload>.csv (RTT per mesaj), aduna toate reps.
Detecteaza coloana RTT automat si afiseaza ce a citit (verifica!).
Folosire: python3 cdf_c1.py <dir_campanie> [conditie=loss_30] [payload=4096]
Iese: <dir>/analysis/fig_cdf_<conditie>.png
"""
import sys, os, glob, csv
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
COND = sys.argv[2] if len(sys.argv) > 2 else "loss_30"
PL   = sys.argv[3] if len(sys.argv) > 3 else "4096"
COL = {"cyclonedds": "#1f77b4", "zenoh": "#9467bd"}

def is_num(x):
    try: float(x); return True
    except Exception: return False

def pick_col(header):
    """alege indexul coloanei RTT din header"""
    low = [h.lower() for h in header]
    for key in ("rtt", "latenc", "lat_ms", "_ms", "ms"):
        for i,h in enumerate(low):
            if key in h: return i
    return None

def read_rtts(path):
    rows = list(csv.reader(open(path)))
    if not rows: return [], "gol"
    first = rows[0]
    has_header = not all(is_num(c) for c in first)
    if has_header:
        idx = pick_col(first)
        body = rows[1:]
        if idx is None:  # nicio coloana evidenta -> ultima numerica
            idx = max(i for i,c in enumerate(rows[1] if len(rows)>1 else first) if is_num(c))
        label = first[idx]
    else:
        body = rows
        idx = 0 if len(first)==1 else len(first)-1  # 1 col -> ea; altfel ultima
        label = f"col[{idx}] (fara antet)"
    vals = []
    for r in body:
        if idx < len(r) and is_num(r[idx]): vals.append(float(r[idx]))
    return vals, label

data = {}; detected = {}
for cf in glob.glob(os.path.join(ROOT,"*",COND,"rep*",f"transport_p{PL}.csv")):
    rmw = cf.split(os.sep)[-4]
    vals, lab = read_rtts(cf)
    if vals:
        data.setdefault(rmw,[]).extend(vals); detected[rmw]=lab
if not data: sys.exit(f"[!] niciun transport_p{PL}.csv pentru {COND} sub {ROOT}")

fig, ax = plt.subplots(figsize=(9, 5.5))
for r in sorted(data.keys()):
    v = sorted(data[r]); n = len(v)
    y = [(i+1)/n for i in range(n)]
    ax.plot(v, y, color=COL.get(r), label=f"{r} (n={n})", lw=1.8)
    print(f"  {r}: coloana detectata='{detected[r]}', n={n}, "
          f"min={v[0]:.1f} median={v[n//2]:.1f} max={v[-1]:.1f} ms")
ax.set_xlabel("RTT [ms]", fontsize=11)
ax.set_ylabel("probabilitate cumulata (CDF)", fontsize=11)
ax.set_title(f"Distributia RTT (CDF) -- conditia '{COND}', sarcina utila {PL} B", fontsize=12)
ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6); ax.set_axisbelow(True)
ax.legend(title="RMW", fontsize=10)
fig.subplots_adjust(left=0.09, right=0.97, top=0.92, bottom=0.18)
fig.text(0.5, 0.02, f"SIL (loopback); conditia '{COND}'; RTT brut agregat pe repetitii "
         f"(sarcina utila {PL} B).", ha="center", va="bottom", fontsize=8.5)
od = os.path.join(ROOT, "analysis"); os.makedirs(od, exist_ok=True)
for ext in ("png", "pdf"):
    plt.savefig(os.path.join(od, f"fig_cdf_{COND}.{ext}"), dpi=200)
print("[ok]", os.path.join(od, f"fig_cdf_{COND}") + ".{png,pdf}")
