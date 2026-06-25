#!/usr/bin/env python3
"""reproduce_selector_mission.py -- SELECTOR cu obiectiv TELEMETRIE (min timp de misiune).

Fisier-FRATE; reutilizeaza selector_core (NU atinge reproduce_pdia.py / PDIA, nici
reproduce_selector.py). Citeste un campaign_summary.csv produs de analyze_campaign.py
(coloane: rmw, condition, mission_time_s, ...) si alege RMW-ul care minimizeaza timpul de
misiune per conditie, cu validare leave-one-condition-out (LOCO) + REGRET.

Misiunea e payload-agnostica -> o celula per conditie (vezi selector_core.build_mission_cells).

ATENTIE (onestitate): are nevoie de date de MISIUNE reale. Campania doar-transport (cea care
produce transport_*_summary.json) NU le contine. Le produci cu o campanie care include stratul
'mission':
    cd ~/ros2_ws && colcon build && source install/setup.bash
    sudo -v   # netem are nevoie de privilegii
    python3 src/c1_benchmark/run_campaign.py --reps 5 --layers transport mission
    python3 src/c1_benchmark/analyze_campaign.py <results_c1/>   # -> campaign_summary.csv
Apoi: python3 reproduce_selector_mission.py <results_c1/analysis/campaign_summary.csv>

Demo rapid (date sintetice, fara ROS):
    python3 analyze_campaign.py --selftest        # scrie selftest_out/campaign_summary.csv
    python3 reproduce_selector_mission.py selftest_out/campaign_summary.csv

Uz:
  python3 reproduce_selector_mission.py <campaign_summary.csv>
  python3 reproduce_selector_mission.py --selftest     # nucleul pur, fara date
"""
import csv
import os
import sys

import selector_core as sc

HERE = os.path.dirname(os.path.abspath(__file__))


def load_summary(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def main(argv):
    if "--selftest" in argv:
        sc._selftest()
        print("OK selftest (nucleu pur).")
        return 0

    path = next((a for a in argv[1:] if not a.startswith("-")), None)
    if not path or not os.path.exists(path):
        print("FATAL: da-mi un campaign_summary.csv (cu coloana mission_time_s).")
        print("  Vezi antetul scriptului: ai nevoie de o campanie cu strat 'mission'.")
        return 1

    rows = load_summary(path)
    if rows and "mission_time_s" not in rows[0]:
        print("FATAL: %s nu are coloana mission_time_s." % path)
        print("  E un campaign_summary produs DOAR pe transport? Ruleaza campania cu strat mission.")
        return 1

    cells = sc.build_mission_cells(rows)
    usable = {k: c for k, c in cells.items() if len(c) >= 2}
    n = len(usable)
    print("Incarcate %d randuri din %s\n" % (len(rows), path))

    print("== Castigator per conditie (obiectiv telemetrie = min timp misiune) ==")
    wins = {r: 0 for r in sc.RMWS}
    for k in sorted(usable):
        cell = usable[k]
        win = sc.cell_winner(cell)
        wins[win] += 1
        vals = "  ".join("%s=%7.1fs" % (r, cell[r]) for r in sc.RMWS if r in cell)
        print("  %-13s  %s  -> %s" % (k[0], vals, win))
    print("  TOTAL %d conditii utilizabile -> %s\n" % (n, wins))

    censored = sorted(k[0] for k in cells if len(cells[k]) < 2)
    if censored:
        print("  cenzurate (lipsa timp pt un RMW, misiune neterminata): %s\n" % censored)

    if n < 2:
        print("Prea putine conditii cu ambele RMW-uri pentru LOCO -- ruleaza o campanie mai larga.")
        return 0

    print("== Baseline-uri de regret (timp misiune, s; oracol = 0) ==")
    for rmw in sc.RMWS:
        tot = sum(sc.regret(rmw, usable[k]) for k in usable if rmw in usable[k])
        print("  always-%-11s regret total=%8.1f  mediu=%6.1f s" % (rmw, tot, tot / n))
    print("  oracol             regret total=%8.1f  mediu=%6.1f s\n" % (0.0, 0.0))

    print("== Selector telemetrie (validare leave-one-condition-out) ==")
    res = sc.evaluate_selector(usable, sc.nn_predict)
    print("  1-NN: acuratete LOCO=%.1f%% (%d/%d conditii); regret mediu/conditie=%.1f s"
          % (100 * res["accuracy"], round(res["accuracy"] * res["n_cells"]),
             res["n_cells"], res["selector_regret_mean"]))

    print("\n== Note oneste ==")
    print("  - obiectiv TELEMETRIE = min timp de misiune (payload-agnostic; o celula/conditie).")
    print("  - timp cenzurat (misiune neterminata) = sarit aici; un obiectiv constient de plafon")
    print("    (timeout = cost maxim) ramane TODO.")
    print("  - SIL/loopback daca campania a fost pe o masina; HIL (doua masini) ramane standardul.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
