#!/usr/bin/env python3
"""make_tables_c2.py -- tabelele analizei SIL C2 (read-only, fara ROS, fara retea).
Nu modifica datele. Doar FAPTE.

T1 grila 4KB SIL: delivery medie+-std, toate 20 celulele (C2_SIL_20260718).
T2 burst-aware la conditiile-cheie: longest burst (max, p95), gap p95, nr rafale.
T3 64KB {bern_15, ge_15_8} x RMW: delivery+-std + nr received=0 (C2_SIL64_20260719).
T4 combo lat200_jit50_ge_15_8 vs ge_15_8 vs bern_15 (4KB) + referinta C1 SIL
   lat200_jit50 (protocol byte-identic, comparabil).
"""
import glob
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from burst_metrics import failure_bursts, load_received, _p95

HOME = os.path.expanduser("~")
D = os.path.join(HOME, "DATE_CAMPANIE")
ROOT4 = os.path.join(D, "C2_SIL_20260718")
ROOT64 = os.path.join(D, "C2_SIL64_20260719")
ROOTCOMBO = os.path.join(D, "C2_SILCOMBO_20260719")
ROOTC1 = os.path.join(D, "SIL", "date")   # C1 SIL canonic (fair 2026-06-24)

CONDS = ["ideal", "bern_5", "ge_5_3", "ge_5_8", "bern_15", "ge_15_3", "ge_15_8",
         "bern_30", "ge_30_3", "ge_30_8"]
RMWS = ["cyclonedds", "zenoh"]


def _reps(root, rmw, cond, payload):
    out = []
    for sj in sorted(glob.glob("%s/%s/%s/rep*/transport_p%d_summary.json" % (root, rmw, cond, payload))):
        d = json.load(open(sj))
        cf = os.path.join(os.path.dirname(sj), "transport_p%d.csv" % payload)
        rs = load_received(cf) if os.path.isfile(cf) else []
        out.append((d, rs))
    return out


def delivery(root, rmw, cond, payload=4096):
    reps = _reps(root, rmw, cond, payload)
    dv = [100.0 * d["received"] / d["sent"] if d["sent"] else 0.0 for d, _ in reps]
    r0 = sum(1 for d, _ in reps if d["received"] == 0)
    sents = [d["sent"] for d, _ in reps]
    return dv, r0, sents


def bursts(root, rmw, cond, payload=4096):
    reps = _reps(root, rmw, cond, payload)
    allb, longest = [], []
    for _, rs in reps:
        b = failure_bursts(rs)
        allb += b
        longest.append(max(b) if b else 0)
    return {"longest_max": max(longest) if longest else 0,
            "longest_p95": _p95(longest) if longest else 0,
            "gap_p95": _p95(allb) if allb else 0, "n_bursts": len(allb)}


def _ms(x):
    return (round(st.mean(x), 1), round(st.pstdev(x), 1)) if x else (float("nan"), float("nan"))


def T1():
    print("== T1: grila 4KB SIL -- delivery %(medie+-std), 20 celule ==")
    print("%-9s %16s %16s" % ("cond", "cyclonedds", "zenoh"))
    rows = {}
    for c in CONDS:
        cells = {}
        line = "%-9s" % c
        for rmw in RMWS:
            dv, r0, _ = delivery(ROOT4, rmw, c)
            m, s = _ms(dv)
            cells[rmw] = (m, s, r0)
            line += " %8.1f+-%-5.1f" % (m, s)
        print(line)
        rows[c] = cells
    return rows


def T2():
    key = ["bern_5", "ge_5_3", "ge_5_8", "bern_15", "ge_15_3", "ge_15_8", "bern_30", "ge_30_3", "ge_30_8"]
    print("\n== T2: burst-aware 4KB (longest max/p95 | gap p95 | nr rafale) ==")
    print("%-9s %-11s %10s %8s %8s" % ("cond", "rmw", "longest", "gapp95", "nburst"))
    for c in key:
        for rmw in RMWS:
            b = bursts(ROOT4, rmw, c)
            print("%-9s %-11s %5d/%-4d %8d %8d" % (c, rmw, b["longest_max"], b["longest_p95"], b["gap_p95"], b["n_bursts"]))


def T3():
    print("\n== T3: 64KB {bern_15, ge_15_8} x RMW -- delivery+-std, recv0 (sent~989) ==")
    print("%-9s %-11s %16s %10s %6s" % ("cond", "rmw", "delivery%", "min-max", "recv0"))
    for c in ("bern_15", "ge_15_8"):
        for rmw in RMWS:
            dv, r0, sents = delivery(ROOT64, rmw, c, 65536)
            m, s = _ms(dv)
            print("%-9s %-11s %8.1f+-%-6.1f %4.1f-%-5.1f %6d" % (c, rmw, m, s, min(dv), max(dv), r0))


def T4():
    print("\n== T4: combo lat200_jit50_ge_15_8 vs ge_15_8 vs bern_15 (4KB) + ref C1 SIL ==")
    print("%-24s %-11s %16s %6s" % ("set/conditie", "rmw", "delivery%", "recv0"))
    for rmw in RMWS:
        dv, r0, _ = delivery(ROOTCOMBO, rmw, "lat200_jit50_ge_15_8")
        m, s = _ms(dv)
        print("%-24s %-11s %8.1f+-%-6.1f %6d" % ("combo(lat+ge_15_8) C2", rmw, m, s, r0))
    for rmw in RMWS:
        dv, r0, _ = delivery(ROOT4, rmw, "ge_15_8")
        m, s = _ms(dv)
        print("%-24s %-11s %8.1f+-%-6.1f %6d" % ("ge_15_8 (4KB) C2", rmw, m, s, r0))
    for rmw in RMWS:
        dv, r0, _ = delivery(ROOT4, rmw, "bern_15")
        m, s = _ms(dv)
        print("%-24s %-11s %8.1f+-%-6.1f %6d" % ("bern_15 (4KB) C2", rmw, m, s, r0))
    for rmw in RMWS:
        dv, r0, _ = delivery(ROOTC1, rmw, "lat200_jit50")
        m, s = _ms(dv)
        print("%-24s %-11s %8.1f+-%-6.1f %6d" % ("lat200_jit50 C1-SIL", rmw, m, s, r0))


def _selftest():
    import tempfile
    d = tempfile.mkdtemp()
    for rep in range(1, 4):
        rd = os.path.join(d, "zenoh", "ge_15_8", "rep%d" % rep)
        os.makedirs(rd)
        open(os.path.join(rd, "transport_p4096.csv"), "w").write("seq,rtt_ms\n1,1\n2,1\n5,1\n")
        json.dump({"sent": 100, "received": 3}, open(os.path.join(rd, "transport_p4096_summary.json"), "w"))
    dv, r0, sents = delivery(d, "zenoh", "ge_15_8")
    assert dv == [3.0, 3.0, 3.0] and r0 == 0 and sents == [100, 100, 100], (dv, r0, sents)
    b = bursts(d, "zenoh", "ge_15_8")
    assert b["longest_max"] == 2 and b["n_bursts"] == 3, b   # gol {3,4} = 2, x3 rep
    m, s = _ms([10.0, 20.0])
    assert m == 15.0 and s == 5.0, (m, s)
    print("SELFTEST make_tables_c2 OK (4 verificari).")


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    T1(); T2(); T3(); T4()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
