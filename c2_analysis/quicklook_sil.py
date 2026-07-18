#!/usr/bin/env python3
"""quicklook_sil.py -- agregare read-only a campaniei C2 SIL (fara ROS, fara retea,
NU atinge tc/netem, NU modifica datele). Doar FAPTE, zero interpretare de ipoteza.

Intrare: un director de campanie <root>/<rmw>/<conditie>/rep<N>/transport_p4096{.csv,
_summary.json}. Per conditie x RMW agrega: completitudine, delivery ratio (medie+-std),
L_real (pierdere medie), B_real (lungime medie rafala din golurile de seq), longest burst
(max + p95 peste repetitii), gap p95, nr rafale, anomalii (received=0, sent<989).

L_real/B_real sunt masurate la nivel de APLICATIE (dupa middleware): QoS RELIABLE poate
retransmite, deci difera de pierderea injectata de netem. Se raporteaza ca atare.
"""
import csv as _csv
import json
import math
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from burst_metrics import failure_bursts, load_received, _p95

CONDS = ["ideal", "bern_5", "ge_5_3", "ge_5_8", "bern_15", "ge_15_3", "ge_15_8",
         "bern_30", "ge_30_3", "ge_30_8"]
RMWS = ["cyclonedds", "zenoh"]
# Tinte din CALIBRARE_GE_C2.md. bern_L: Bernoulli -> B_tinta = 1/(1-L) (rafala medie
# geometrica a unui proces Bernoulli la rata L). ge_L_B: B_tinta = B.
TARGETS = {
    "ideal":   (0.0,  None),
    "bern_5":  (5.0,  1/(1-0.05)),  "bern_15": (15.0, 1/(1-0.15)),  "bern_30": (30.0, 1/(1-0.30)),
    "ge_5_3":  (5.0,  3.0), "ge_5_8":  (5.0,  8.0),
    "ge_15_3": (15.0, 3.0), "ge_15_8": (15.0, 8.0),
    "ge_30_3": (30.0, 3.0), "ge_30_8": (30.0, 8.0),
}


def _cell(root, rmw, cond):
    """Agrega o celula (conditie x RMW) peste repetitii. Intoarce dict de fapte."""
    d = os.path.join(root, rmw, cond)
    reps = sorted(os.path.join(d, r) for r in os.listdir(d)) if os.path.isdir(d) else []
    delivery, losses, p95s = [], [], []
    all_bursts, longest_per_rep = [], []
    n_recv0, n_sent_low, n_missing_csv = 0, 0, 0
    n_reps = 0
    for rd in reps:
        sj = os.path.join(rd, "transport_p4096_summary.json")
        cf = os.path.join(rd, "transport_p4096.csv")
        if not os.path.isfile(sj):
            continue
        n_reps += 1
        s = json.load(open(sj))
        sent, recv = s.get("sent", 0), s.get("received", 0)
        losses.append(s.get("loss", 0.0) * 100.0)
        delivery.append(100.0 * recv / sent if sent else 0.0)
        if s.get("p95_ms") is not None:
            p95s.append(s["p95_ms"])
        if recv == 0:
            n_recv0 += 1
        if sent < 989:
            n_sent_low += 1
        if os.path.isfile(cf):
            b = failure_bursts(load_received(cf))
            all_bursts += b
            longest_per_rep.append(max(b) if b else 0)
        else:
            n_missing_csv += 1
    def ms(x): return (round(st.mean(x), 2), round(st.pstdev(x), 2)) if x else (float('nan'), float('nan'))
    dm, ds = ms(delivery)
    lm = round(st.mean(losses), 3) if losses else float('nan')
    return {
        "n_reps": n_reps,
        "delivery_mean": dm, "delivery_std": ds,
        "L_real": lm,
        "p95_ms_mean": round(st.mean(p95s), 1) if p95s else float('nan'),
        "B_real": round(st.mean(all_bursts), 3) if all_bursts else 0.0,
        "gap_p95": _p95(all_bursts) if all_bursts else 0,
        "longest_max": max(longest_per_rep) if longest_per_rep else 0,
        "longest_p95": _p95(longest_per_rep) if longest_per_rep else 0,
        "n_bursts_total": len(all_bursts),
        "n_recv0": n_recv0, "n_sent_low": n_sent_low, "n_missing_csv": n_missing_csv,
    }


def analyze(root):
    return {(rmw, c): _cell(root, rmw, c) for rmw in RMWS for c in CONDS}


def _selftest():
    import tempfile
    d = tempfile.mkdtemp()
    # o celula sintetica: 2 rep, received 11,12,14 (gol la 13) -> burst [1]
    for rep in (1, 2):
        rd = os.path.join(d, "cyclonedds", "ge_5_3", "rep%d" % rep)
        os.makedirs(rd)
        open(os.path.join(rd, "transport_p4096.csv"), "w").write("seq,rtt_ms\n11,1\n12,1\n14,1\n")
        json.dump({"sent": 100, "received": 3, "loss": 0.97, "p95_ms": 5.0},
                  open(os.path.join(rd, "transport_p4096_summary.json"), "w"))
    c = _cell(d, "cyclonedds", "ge_5_3")
    assert c["n_reps"] == 2, c
    assert c["B_real"] == 1.0 and c["longest_max"] == 1, c
    assert c["n_bursts_total"] == 2, c
    assert abs(c["L_real"] - 97.0) < 1e-6, c
    print("SELFTEST quicklook_sil OK (5 verificari).")


def _fmt(v, nd=2):
    return "nan" if isinstance(v, float) and math.isnan(v) else (("%%.%df" % nd) % v if isinstance(v, float) else str(v))


def main(argv):
    if not argv or argv[0] == "--selftest":
        _selftest(); return 0
    root = argv[0]
    R = analyze(root)
    print("== COMPLETITUDINE + ANOMALII (per conditie x RMW) ==")
    print("%-9s %-11s %4s %6s %8s %8s %8s" % ("cond","rmw","reps","recv0","sent<989","noCSV",""))
    for c in CONDS:
        for rmw in RMWS:
            x = R[(rmw, c)]
            print("%-9s %-11s %4d %6d %8d %8d" % (c, rmw, x["n_reps"], x["n_recv0"], x["n_sent_low"], x["n_missing_csv"]))
    print("\n== CALIBRARE (L,B real vs tinta; per RMW; app-level, dupa middleware) ==")
    print("%-9s %-11s %8s %8s %8s %8s %6s" % ("cond","rmw","L_tinta","L_real","B_tinta","B_real","|dL|"))
    for c in CONDS:
        Lt, Bt = TARGETS[c]
        for rmw in RMWS:
            x = R[(rmw, c)]
            dL = abs(x["L_real"] - Lt) if not math.isnan(x["L_real"]) else float('nan')
            print("%-9s %-11s %8.1f %8s %8s %8s %6s" % (
                c, rmw, Lt, _fmt(x["L_real"],2), _fmt(Bt,2) if Bt else "-", _fmt(x["B_real"],2), _fmt(dL,2)))
    print("\n== METRICI (per conditie x RMW) ==")
    print("%-9s %-11s %14s %8s %8s %8s %7s" % ("cond","rmw","deliv%(m+-std)","Lreal%","longest","gapp95","nburst"))
    for c in CONDS:
        for rmw in RMWS:
            x = R[(rmw, c)]
            print("%-9s %-11s %6s+-%-6s %8s %8s %8s %7d" % (
                c, rmw, _fmt(x["delivery_mean"],1), _fmt(x["delivery_std"],1),
                _fmt(x["L_real"],2), "%d/%d"%(x["longest_max"],x["longest_p95"]),
                x["gap_p95"], x["n_bursts_total"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
