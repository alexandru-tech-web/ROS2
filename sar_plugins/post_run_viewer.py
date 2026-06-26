#!/usr/bin/env python3
"""post_run_viewer.py -- vizualizator OFFLINE post-rulare: descopera CSV-urile unei campanii
(SIL sau HIL) sub --root, le rezuma (post_run_core) si produce un tabel + o figura. Frontend
subtire (logica + testele sunt in post_run_core.py). Separa vizual gilbert_* (pierdere CORELATA)
de loss_* (independenta).
Ruleaza: python3 post_run_viewer.py --root <results_dir> [--out <dir>]"""
import argparse
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post_run_core as prc

COL = {"cyclonedds": "#1f77b4", "zenoh": "#9467bd"}


def walk_transport(root):
    """{(rmw, cond): [rtt_p95...]} din <rmw>/<cond>/rep*/transport_p*.csv."""
    cells = {}
    for f in sorted(glob.glob(os.path.join(root, "*", "*", "rep*", "transport_p*.csv"))):
        parts = f.split(os.sep)
        rmw, cond = parts[-4], parts[-3]
        with open(f) as fh:
            st = prc.summarize_transport(prc.read_rows(fh.read()))
        if st["n"]:
            cells.setdefault((rmw, cond), []).append(st["rtt_p95_ms"])
    return cells


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv[1:])

    root = a.root
    if (not glob.glob(os.path.join(root, "*", "*", "rep*", "transport_p*.csv"))
            and os.path.isdir(os.path.join(root, "c1_transport"))):
        root = os.path.join(root, "c1_transport")
    out = a.out or os.path.join(root, "post_run")
    os.makedirs(out, exist_ok=True)

    cells = walk_transport(root)
    if not cells:
        print("[!] niciun transport_p*.csv sub %s" % root)
        return 1
    rmws = sorted({k[0] for k in cells})
    conds = sorted({k[1] for k in cells})

    sumpath = os.path.join(out, "post_run_summary.csv")
    with open(sumpath, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rmw", "condition", "n_rep", "rtt_p95_mean_ms"])
        for rmw in rmws:
            for c in conds:
                vals = cells.get((rmw, c))
                if vals:
                    w.writerow([rmw, c, len(vals), round(prc.mean(vals), 1)])
    print("[ok] %s" % sumpath)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("(matplotlib indisponibil -- doar CSV)")
        return 0

    x = list(range(len(conds)))
    wbar = 0.8 / max(1, len(rmws))
    fig, ax = plt.subplots(figsize=(9, 5.0))
    for j, rmw in enumerate(rmws):
        ys = [prc.mean(cells.get((rmw, c), [0.0])) or 0.0 for c in conds]
        ax.bar([i + j * wbar for i in x], ys, wbar, label=rmw, color=COL.get(rmw, "#888"),
               edgecolor="black", linewidth=0.5)
    ax.set_xticks([i + wbar * (len(rmws) - 1) / 2 for i in x])
    labels = [("[burst] " + c if c.startswith("gilbert") else c) for c in conds]
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)
    ax.set_xlabel("conditie (gilbert_* = pierdere CORELATA)", fontsize=11)
    ax.set_ylabel("RTT p95 mediu [ms]", fontsize=11)
    ax.set_title("Post-rulare: RTT p95 per conditie (gilbert_* vs loss_*)", fontsize=12)
    ax.legend(title="RMW", fontsize=10)
    ax.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    fig.subplots_adjust(bottom=0.24)
    fig.text(0.5, 0.02, "Vizualizator generic SIL/HIL; gilbert_* = pierdere in rafale.",
             ha="center", fontsize=8.5)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(out, "post_run_rtt." + ext), dpi=200)
    print("[ok] %s.{png,pdf}" % os.path.join(out, "post_run_rtt"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
