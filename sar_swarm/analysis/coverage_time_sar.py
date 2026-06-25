#!/usr/bin/env python3
"""coverage_time_sar.py -- curbele de acoperire in timp, per scenariu SIL.
Arata DINAMICA misiunii: unde scenariile degradate incetinesc sau plafoneaza.
Folosire: python3 coverage_time_sar.py <dir_cu_sil_metrics_csv>
Iese: <dir>/fig_coverage_time.png
"""
import sys, os, glob, csv
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
files = sorted(glob.glob(os.path.join(ROOT, "*_metrics.csv")))
if not files: sys.exit("[!] niciun *_metrics.csv in "+ROOT)

fig, ax = plt.subplots(figsize=(10,5.5))
for f in files:
    name = os.path.basename(f).replace("_metrics.csv","")
    ts, cov = [], []
    with open(f) as fh:
        r = csv.DictReader(fh)
        for row in r:
            try:
                ts.append(float(row["t_s"])); cov.append(float(row["coverage"])*100)
            except (KeyError, ValueError):
                continue
    if ts: ax.plot(ts, cov, lw=1.8, label=name)
ax.set_xlabel("Timp [s]"); ax.set_ylabel("Acoperire [%]")
ax.set_ylim(0,100)
ax.set_title("Dinamica acoperirii in timp, per scenariu (SIL)")
ax.grid(True, alpha=0.3); ax.legend(fontsize=8, ncol=2)
plt.tight_layout()
out = os.path.join(ROOT,"fig_coverage_time.png"); plt.savefig(out, dpi=150); print("[ok]", out)
