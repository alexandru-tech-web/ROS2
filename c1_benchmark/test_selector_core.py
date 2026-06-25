#!/usr/bin/env python3
"""test_selector_core.py -- verificari pure pentru selector_core (fara ROS/sklearn/I/O).

Ruleaza: python3 test_selector_core.py
"""
import selector_core as sc

N = 0


def ok(cond, msg):
    global N
    assert cond, "ESEC: " + msg
    N += 1
    print("  [ok] " + msg)


def main():
    print("== 1. parsarea conditiei in parametri netem reali ==")
    ok(sc.parse_cond("ideal") == (0.0, 0.0, 0.0), "ideal -> (0,0,0)")
    ok(sc.parse_cond("loss_30") == (30.0, 0.0, 0.0), "loss_30 -> loss=30")
    ok(sc.parse_cond("lat200_jit50") == (0.0, 200.0, 50.0), "lat200_jit50 -> lat=200 jit=50")
    ok(sc.parse_cond("lat200_l15") == (15.0, 200.0, 0.0), "lat200_l15 -> loss=15 lat=200")
    try:
        sc.parse_cond("xyz")
        raise AssertionError("trebuia ValueError")
    except ValueError:
        ok(True, "conditie necunoscuta ridica ValueError")

    print("== 2. feature-urile celulei ==")
    f = sc.cell_features("loss_15", 4096)
    ok(f[0] == 15.0 and f[1] == 0.0 and f[2] == 0.0, "loss_15 -> [15,0,0,...]")
    ok(abs(sc.cell_features("x" if False else "ideal", 100)[3] - 2.0) < 1e-9, "log10(100)=2")
    ok(abs(sc.cell_features("ideal", 65536)[3] - 4.816) < 1e-3, "log10(65536)~4.816")

    print("== 3. agregarea pe celule (mediana peste repetitii) ==")
    rows = [
        {"cond": "ideal", "payload": "64", "rmw": "cyclonedds", "rtt_p95_ms": "1.0"},
        {"cond": "ideal", "payload": "64", "rmw": "cyclonedds", "rtt_p95_ms": "3.0"},
        {"cond": "ideal", "payload": "64", "rmw": "zenoh", "rtt_p95_ms": "5.0"},
    ]
    cells = sc.build_cells(rows)
    ok(cells[("ideal", 64)]["cyclonedds"] == 2.0, "mediana(1,3)=2 pe cyclonedds")
    ok(("ideal", 64) in cells and len(cells) == 1, "o singura celula construita")

    print("== 4. castigator si regret ==")
    cell = {"cyclonedds": 2.0, "zenoh": 5.0}
    ok(sc.cell_winner(cell) == "cyclonedds", "castigator = min RTT p95")
    ok(sc.regret("cyclonedds", cell) == 0.0, "regret oracol = 0")
    ok(sc.regret("zenoh", cell) == 3.0, "regret alegere gresita = diferenta")

    print("== 5. LOCO: testul e o conditie intreaga, train exclude conditia ==")
    keys = [("loss_15", 64), ("loss_15", 4096), ("loss_30", 64), ("loss_30", 4096)]
    folds = sc.loco_folds(keys)
    ok(len(folds) == 2, "doua conditii -> doua fold-uri")
    for held, train, test in folds:
        ok(all(k[0] == held for k in test), "test = doar conditia %s" % held)
        ok(all(k[0] != held for k in train), "train nu contine %s" % held)

    print("== 6. selector 1-NN + evaluare (winner flip cu payload) ==")
    cflip = {
        ("loss_15", 64): {"cyclonedds": 1.0, "zenoh": 2.0},
        ("loss_15", 65536): {"cyclonedds": 9.0, "zenoh": 3.0},
        ("loss_30", 64): {"cyclonedds": 1.0, "zenoh": 5.0},
        ("loss_30", 65536): {"cyclonedds": 9.0, "zenoh": 4.0},
    }
    res = sc.evaluate_selector(cflip, sc.nn_predict)
    ok(res["n_cells"] == 4, "4 celule evaluate")
    ok(res["oracle_regret_total"] == 0.0, "oracol regret total = 0")
    ok(res["always_cyclonedds_regret_total"] > 0.0, "always-cyclone plateste regret pe payload mare")
    ok(res["always_zenoh_regret_total"] > 0.0, "always-zenoh plateste regret pe payload mic")
    ok(res["selector_regret_total"] >= 0.0, "regret selector >= 0 (nu bate oracolul)")
    ok(0.0 <= res["accuracy"] <= 1.0, "acuratete in [0,1]")

    print("== 7. selftest-ul intern al modulului ==")
    sc._selftest()
    ok(True, "selector_core._selftest() a trecut")

    print("\nTOATE TESTELE SELECTOR_CORE AU TRECUT: %d verificari." % N)


if __name__ == "__main__":
    main()
