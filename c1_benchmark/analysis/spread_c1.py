#!/usr/bin/env python3
"""spread_c1.py -- imprastierea per-conditie a celor N repetitii.
Citeste p95_ms si loss din transport_p<REF>_summary.json (acelasi REF ca analyze,
implicit 4096) pentru fiecare rep si raporteaza media +/- std + interval de
incredere 95% (t-Student). Arata daca varianta IN sesiune e mica.

Folosire: python3 spread_c1.py <dir_campanie> [REF_payload]
"""
import sys, os, glob, json, math, statistics

REF = int(sys.argv[2]) if len(sys.argv) > 2 else 4096

# t critic, 95% two-sided, pe grade de libertate (df = N-1)
T95 = {1:12.706, 2:4.303, 3:3.182, 4:2.776, 5:2.571, 6:2.447, 7:2.365,
       8:2.306, 9:2.262, 10:2.228, 11:2.201, 12:2.179, 13:2.160, 14:2.145,
       15:2.131, 16:2.120, 18:2.101, 20:2.086, 25:2.060, 30:2.042}

def tval(df):
    if df <= 0: return float("nan")
    if df in T95: return T95[df]
    if df > 30: return 1.96
    lo = max(k for k in T95 if k <= df)
    return T95[lo]

def desc(vals):
    n = len(vals)
    if n == 0: return None
    m = statistics.mean(vals)
    sd = statistics.stdev(vals) if n > 1 else 0.0
    ci = tval(n - 1) * sd / math.sqrt(n) if n > 1 else 0.0
    return n, m, sd, ci, min(vals), max(vals)

def main(root):
    rmws = sorted(os.path.basename(p) for p in glob.glob(os.path.join(root, "*"))
                  if os.path.isdir(p) and os.path.basename(p) != "analysis")
    print(f"REF payload = {REF} B\n")
    hdr = (f"{'rmw':<11}{'conditie':<10}{'N':>3} | {'p95 medie':>9} {'std':>6} "
           f"{'CI95+/-':>7} {'min':>6} {'max':>6} | {'pierdere':>8} {'std':>5}")
    print(hdr); print("-" * len(hdr))
    nfiles = 0
    for r in rmws:
        conds = sorted(os.path.basename(p)
                       for p in glob.glob(os.path.join(root, r, "*"))
                       if os.path.isdir(p))
        for c in conds:
            p95s, losses = [], []
            for sj in glob.glob(os.path.join(root, r, c, "rep*",
                                             f"transport_p{REF}_summary.json")):
                nfiles += 1
                d = json.load(open(sj))
                if d.get("p95_ms") is not None:
                    p95s.append(d["p95_ms"])
                losses.append(d.get("loss", 0.0))
            sp = desc(p95s); sl = desc(losses)
            if not sp:
                continue
            n, m, sd, ci, mn, mx = sp
            lm, lsd = sl[1], sl[2]
            print(f"{r:<11}{c:<10}{n:>3} | {m:>8.0f}m {sd:>6.0f} {ci:>7.0f} "
                  f"{mn:>6.0f} {mx:>6.0f} | {lm*100:>7.1f}% {lsd*100:>5.1f}")
    if nfiles == 0:
        print(f"\n[!] 0 fisiere transport_p{REF}_summary.json gasite -- "
              f"incearca alt REF (ex: python3 spread_c1.py <dir> 65536)")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
