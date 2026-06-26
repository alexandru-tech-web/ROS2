#!/usr/bin/env python3
"""test_rf_interference.py -- verificari pure pentru rf_interference (fara ROS / I-O).
Ruleaza din sar_plugins/: python3 test_rf_interference.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rf_interference as rf

N = 0


def ok(cond, msg):
    global N
    assert cond, "ESEC: " + msg
    N += 1
    print("  [ok] " + msg)


def empirical_mean_burst(bp, n=200000):
    """Lungimea medie a rafalelor de PIERDERI consecutive in n trageri."""
    runs, cur = [], 0
    for _ in range(n):
        if bp.draw():
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    return sum(runs) / len(runs) if runs else 0.0


def main():
    print("== 1. statistici stationare ==")
    bp = rf.BurstProcess(p=0.1, r=0.4, seed=1)
    ok(abs(bp.steady_loss - 0.2) < 1e-12, "steady_loss = p/(p+r) la Gilbert simplu")
    ok(abs(bp.mean_burst_len - 2.5) < 1e-12, "mean_burst_len = 1/r")

    print("== 2. media empirica a pierderii ~ steady_loss ==")
    bp2 = rf.BurstProcess(p=0.05, r=0.2, seed=7)
    emp = sum(bp2.draw() for _ in range(200000)) / 200000
    ok(abs(emp - bp2.steady_loss) < 0.01,
       "pierdere empirica ~ stationara (%.3f vs %.3f)" % (emp, bp2.steady_loss))

    print("== 3. rafale: lungimea empirica creste cu mean_burst_len ==")
    bL = rf.BurstProcess.from_steady(0.3, 8.0, seed=3)
    eb = empirical_mean_burst(bL)
    ok(eb > 3.0, "rafale lungi la mean_burst_len=8 (empiric %.1f >> 1)" % eb)
    bS = rf.BurstProcess.from_steady(0.3, 1.2, seed=3)
    es = empirical_mean_burst(bS)
    ok(es < eb, "rafale mai scurte cand mean_burst_len e mic (%.1f < %.1f)" % (es, eb))

    print("== 4. determinism cu seed ==")
    a = [rf.BurstProcess(0.1, 0.3, seed=9).draw() for _ in range(500)]
    b = [rf.BurstProcess(0.1, 0.3, seed=9).draw() for _ in range(500)]
    ok(a == b, "acelasi seed -> aceeasi secventa")

    print("== 5. from_steady recupereaza tinta ==")
    bt = rf.BurstProcess.from_steady(0.25, 5.0)
    ok(abs(bt.steady_loss - 0.25) < 1e-9 and abs(bt.mean_burst_len - 5.0) < 1e-9,
       "steady=0.25, burst=5 recuperate")

    print("== 6. paritate netem gemodel ==")
    s = bp.to_netem_gemodel()
    ok(s.startswith("loss gemodel ") and s.count("%") == 4,
       "sintaxa 'loss gemodel ...' cu 4 procente")
    p, r, lb, lg = rf.parse_netem_gemodel(s)
    ok(abs(p - 0.1) < 1e-3 and abs(r - 0.4) < 1e-3 and abs(lb - 1.0) < 1e-3,
       "round-trip parametri")

    print("== 7. co-canal SINR ==")
    s0, i0 = rf.cochannel_sinr(-60.0, [])
    s1, i1 = rf.cochannel_sinr(-60.0, [-80.0])
    s2, i2 = rf.cochannel_sinr(-60.0, [-80.0, -75.0])
    ok(s0 > s1 > s2, "SINR scade cu nr. interferenti")
    ok(0.0 == i0 < i1 < i2, "interference_db creste de la 0")

    print("== 8. conditions_gilbert ==")
    cg = rf.conditions_gilbert()
    ok(set(cg) == {"gilbert_20", "gilbert_25", "gilbert_30"}, "3 conditii gilbert_*")
    ok(abs(cg["gilbert_30"]["loss"] - 0.30) < 1e-9, "gilbert_30 are pierderea medie 0.30")

    print("== 9. selftest intern al modulului ==")
    rf._selftest()
    ok(True, "rf_interference._selftest() a trecut")

    print("\nTOATE TESTELE RF_INTERFERENCE AU TRECUT: %d verificari." % N)


if __name__ == "__main__":
    main()
