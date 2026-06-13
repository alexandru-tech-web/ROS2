#!/usr/bin/env python3
"""analyze_campaign.py - agrega o campanie RMW (Zenoh vs Cyclone) si scoate figuri.

Citeste arborele:
    <camp>/<rmw>/<conditie>/rep<k>/robot_log.csv
si calculeaza, pentru fiecare rulare, metrici de APLICATIE fata de tinta (gx,gy):
  - reusita (a ajuns la tinta in arrive_r ?),
  - timp pana la tinta [s],
  - eroare transversala de traseu CTE (medie si maxima) fata de linia start->tinta.
Apoi agrega pe (rmw, conditie) cu medie +/- abatere peste repetari si deseneaza:
  fig_reusita.png, fig_timp.png, fig_cte.png  + summary.csv

Complementar lui analyze_perception.py (care compara doua rulari); aici e
intreaga campanie cu sweep si repetari.

  python3 analyze_campaign.py --camp results/campaign_XXXX --goal 8 3
Optional, daca jurnalul are alte coloane:
  --xcol x --ycol y --tcol t --arrive 0.5
"""
import argparse
import csv
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

XCANDS = ["x", "px", "pos_x", "rover_x"]
YCANDS = ["y", "py", "pos_y", "rover_y"]
TCANDS = ["t_s", "t", "time", "stamp", "sec", "secs"]


def _pick(header, cands, override):
    if override and override in header:
        return override
    low = {h.lower(): h for h in header}
    for c in cands:
        if c in low:
            return low[c]
    return None


def read_log(path, xcol, ycol, tcol):
    with open(path, newline="") as f:
        rd = csv.DictReader(f)
        if rd.fieldnames is None:
            return None
        hx = _pick(rd.fieldnames, XCANDS, xcol)
        hy = _pick(rd.fieldnames, YCANDS, ycol)
        ht = _pick(rd.fieldnames, TCANDS, tcol)
        if not (hx and hy):
            raise SystemExit(f"Nu gasesc coloane x/y in {path}. Antet: {rd.fieldnames}. "
                             f"Foloseste --xcol/--ycol/--tcol.")
        t, x, y = [], [], []
        for i, row in enumerate(rd):
            try:
                x.append(float(row[hx])); y.append(float(row[hy]))
                t.append(float(row[ht]) if ht else float(i))
            except (ValueError, KeyError):
                continue
    if len(x) < 2:
        return None
    return np.array(t), np.array(x), np.array(y)


def metrics(t, x, y, gx, gy, arrive):
    sx, sy = x[0], y[0]
    d_goal = np.hypot(x - gx, y - gy)
    hit = np.where(d_goal <= arrive)[0]
    success = len(hit) > 0
    ttg = float(t[hit[0]] - t[0]) if success else float("nan")
    end = hit[0] + 1 if success else len(x)
    # CTE fata de linia start->tinta
    vx, vy = gx - sx, gy - sy
    L = math.hypot(vx, vy) or 1e-9
    px, py = x[:end] - sx, y[:end] - sy
    cte = np.abs(px * vy - py * vx) / L
    return {"success": float(success), "ttg": ttg,
            "cte_mean": float(np.mean(cte)), "cte_max": float(np.max(cte))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camp", required=True)
    ap.add_argument("--goal", nargs=2, type=float, required=True)
    ap.add_argument("--arrive", type=float, default=0.5)
    ap.add_argument("--xcol"); ap.add_argument("--ycol"); ap.add_argument("--tcol")
    a = ap.parse_args()
    gx, gy = a.goal

    rmws = sorted(d for d in os.listdir(a.camp)
                  if os.path.isdir(os.path.join(a.camp, d)))
    conds = sorted({c for r in rmws
                    for c in os.listdir(os.path.join(a.camp, r))
                    if os.path.isdir(os.path.join(a.camp, r, c))})
    if not rmws or not conds:
        raise SystemExit(f"Campanie goala in {a.camp}")

    agg = {}   # (rmw, cond) -> dict de liste
    for r in rmws:
        for c in conds:
            cdir = os.path.join(a.camp, r, c)
            if not os.path.isdir(cdir):
                continue
            vals = {"success": [], "ttg": [], "cte_mean": [], "cte_max": []}
            for rep in sorted(os.listdir(cdir)):
                log = os.path.join(cdir, rep, "robot_log.csv")
                if not os.path.isfile(log):
                    continue
                got = read_log(log, a.xcol, a.ycol, a.tcol)
                if got is None:
                    continue
                m = metrics(*got, gx, gy, a.arrive)
                for k in vals:
                    vals[k].append(m[k])
            agg[(r, c)] = vals

    # summary.csv
    out_csv = os.path.join(a.camp, "summary.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rmw", "conditie", "n", "reusita", "timp_med_s", "timp_std_s",
                    "cte_med_m", "cte_max_m"])
        for r in rmws:
            for c in conds:
                v = agg.get((r, c), {"success": [], "ttg": [], "cte_mean": [], "cte_max": []})
                n = len(v["success"])
                succ = np.mean(v["success"]) if n else float("nan")
                ttg_ok = [x for x in v["ttg"] if not math.isnan(x)]
                w.writerow([r, c, n,
                            f"{succ:.2f}",
                            f"{np.mean(ttg_ok):.1f}" if ttg_ok else "NA",
                            f"{np.std(ttg_ok):.1f}" if ttg_ok else "NA",
                            f"{np.mean(v['cte_mean']):.2f}" if n else "NA",
                            f"{np.mean(v['cte_max']):.2f}" if n else "NA"])
    print(f"[ok] {out_csv}")

    # ---- figuri: bare grupate Zenoh vs Cyclone pe conditii ----
    xpos = np.arange(len(conds))
    width = 0.8 / max(1, len(rmws))
    colors = {"zenoh": "#1f8fff", "cyclone": "#ff7f0e"}

    def grouped(metric_fn, ylabel, title, fname, err_fn=None):
        fig, ax = plt.subplots(figsize=(8, 4.5), dpi=130)
        for i, r in enumerate(rmws):
            ys = [metric_fn(agg.get((r, c), None)) for c in conds]
            errs = [err_fn(agg.get((r, c), None)) for c in conds] if err_fn else None
            ax.bar(xpos + i * width, ys, width, yerr=errs, capsize=3,
                   label=r, color=colors.get(r, None), edgecolor="white")
        ax.set_xticks(xpos + width * (len(rmws) - 1) / 2)
        ax.set_xticklabels(conds, rotation=15)
        ax.set_ylabel(ylabel); ax.set_title(title)
        ax.legend(title="RMW"); ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        p = os.path.join(a.camp, fname)
        fig.savefig(p); plt.close(fig)
        print(f"[ok] {p}")

    def m_succ(v):
        return np.mean(v["success"]) * 100 if v and v["success"] else 0.0

    def m_ttg(v):
        ok = [x for x in v["ttg"] if not math.isnan(x)] if v else []
        return np.mean(ok) if ok else 0.0

    def e_ttg(v):
        ok = [x for x in v["ttg"] if not math.isnan(x)] if v else []
        return np.std(ok) if ok else 0.0

    def m_cte(v):
        return np.mean(v["cte_mean"]) if v and v["cte_mean"] else 0.0

    def e_cte(v):
        return np.std(v["cte_mean"]) if v and v["cte_mean"] else 0.0

    grouped(m_succ, "reusita [%]", "Reusita misiunii vs conditie de retea", "fig_reusita.png")
    grouped(m_ttg, "timp pana la tinta [s]", "Timp pana la tinta (medie +/- std)", "fig_timp.png", e_ttg)
    grouped(m_cte, "CTE mediu [m]", "Eroare transversala de traseu (medie +/- std)", "fig_cte.png", e_cte)

    print("\nRezumat (vezi summary.csv):")
    os.system(f"column -s, -t {out_csv} 2>/dev/null || cat {out_csv}")


if __name__ == "__main__":
    main()
