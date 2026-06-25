#!/usr/bin/env python3
"""reproduce_selector.py -- driverul SELECTORULUI de middleware (obiectiv CONTROL).

Fisier-FRATE al lui reproduce_pdia.py; NU il atinge si NU atinge figurile PDIA.

Ce face:
  1. Citeste ml_dataset.csv si verifica proveniente (loss_pct, sent vs recv, mission_time).
  2. Construieste 18 celule (cond x payload) si afiseaza castigatorul per celula
     (obiectiv control = min RTT p95) -- reproduce 10/18 cyclonedds, 8/18 zenoh.
  3. Evalueaza selectoare cu validare leave-one-condition-out (LOCO):
       - 1-NN transparent (selector_core, fara dependinte);
       - DecisionTree (sklearn, daca e disponibil).
  4. Raporteaza acuratete + REGRET (RTT p95, ms) fata de always-cyclonedds /
     always-zenoh / oracol, si salveaza selector_regret.png.

Uz:
  python3 reproduce_selector.py [date.csv]                                # obiectiv control (RTT p95)
  python3 reproduce_selector.py selector_dataset.csv --objective lossaware [--penalty 1000]
  python3 reproduce_selector.py --selftest                                # nucleul pur, fara date
"""
import csv
import os
import sys

import selector_core as sc

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.join(HERE, "ml_dataset.csv")


def load_rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def provenance_report(rows):
    """Verifica onest ce masoara coloanele de pierdere si daca exista timp de misiune."""
    print("== Proveniente (verificare onesta inainte de articol) ==")
    cols = list(rows[0].keys())
    print("  coloane: %s" % cols)
    loss_vals = sorted({r.get("loss_pct", "") for r in rows})
    sent_eq_recv = all(int(r["sent"]) == int(r["recv"]) for r in rows if "sent" in r and "recv" in r)
    if len(loss_vals) > 12:
        nums = sorted(float(v) for v in loss_vals if v not in ("", None))
        print("  loss_pct: %d valori distincte, interval %.1f..%.1f" % (len(loss_vals), nums[0], nums[-1]))
    else:
        print("  loss_pct distinct: %s" % loss_vals)
    print("  sent == recv pe toate randurile: %s" % sent_eq_recv)
    if loss_vals == ["0.0"] and sent_eq_recv:
        print("  VERDICT: setul NU contine semnal de pierdere (livrare fiabila); netem")
        print("           apare ca LATENTA, nu ca esantioane pierdute. Feature-ul 'loss %'")
        print("           se deriva din NUMELE conditiei, nu din coloana loss_pct.")
    has_mission = any("mission" in c.lower() or "timp" in c.lower() for c in cols)
    print("  coloana de timp de misiune: %s -> obiectivul 'telemetrie' %s"
          % (has_mission, "disponibil" if has_mission else "INDISPONIBIL (doar CONTROL)"))
    print()


def show_cells(cells, title="obiectiv control = min RTT p95"):
    print("== Castigator per (cond x payload), %s ==" % title)
    wins = {r: 0 for r in sc.RMWS}
    for k in sorted(cells):
        cell = cells[k]
        if len(cell) < 2:
            continue
        win = sc.cell_winner(cell)
        wins[win] += 1
        cyc = cell.get("cyclonedds", float("nan"))
        zen = cell.get("zenoh", float("nan"))
        flip = ""
        print("  %-13s pl=%6d  cyclone=%9.1f  zenoh=%9.1f  -> %s%s"
              % (k[0], k[1], cyc, zen, win, flip))
    total = sum(wins.values())
    print("  TOTAL %d celule -> %s" % (total, wins))
    print()
    return wins


def sklearn_predict_factory():
    try:
        from sklearn.tree import DecisionTreeClassifier
    except Exception:
        return None

    def predict(train_feats, train_labels, query):
        clf = DecisionTreeClassifier(max_depth=3, random_state=0)
        clf.fit(train_feats, train_labels)
        return clf.predict([query])[0]

    return predict


def report_eval(name, res):
    print("  [%s]" % name)
    print("     acuratete LOCO        : %.1f%% (%d/%d celule)"
          % (100 * res["accuracy"], round(res["accuracy"] * res["n_cells"]), res["n_cells"]))
    print("     regret total (ms)     : %.0f" % res["selector_regret_total"])
    print("     regret mediu/celula   : %.1f ms" % res["selector_regret_mean"])


def main(argv):
    if "--selftest" in argv:
        sc._selftest()
        print("OK selftest (nucleu pur).")
        return 0

    skip = set()
    objective, penalty = "control", 1000.0
    if "--objective" in argv:
        i = argv.index("--objective"); objective = argv[i + 1]; skip.add(i + 1)
    if "--penalty" in argv:
        i = argv.index("--penalty"); penalty = float(argv[i + 1]); skip.add(i + 1)
    pos = [a for j, a in enumerate(argv) if j >= 1 and not a.startswith("-") and j not in skip]
    path = pos[0] if pos else DEFAULT_CSV
    if not os.path.exists(path):
        print("FATAL: lipseste %s" % path)
        return 1
    rows = load_rows(path)
    print("Incarcate %d randuri din %s (obiectiv: %s)\n" % (len(rows), path, objective))

    provenance_report(rows)
    if objective == "lossaware":
        cells = sc.build_cost_cells(rows, penalty)
        show_cells(cells, title="obiectiv loss-aware = min cost asteptat (D=%.0f ms)" % penalty)
    else:
        cells = sc.build_cells(rows, metric="rtt_p95_ms")
        show_cells(cells, title="obiectiv control = min RTT p95")

    n = len([k for k in cells if len(cells[k]) >= 2])
    unit = "cost ms" if objective == "lossaware" else "RTT p95, ms"
    print("== Baseline-uri de regret (%s; oracol = 0) ==" % unit)
    for rmw in sc.RMWS:
        tot = sum(sc.regret(rmw, cells[k]) for k in cells if rmw in cells[k])
        print("  always-%-11s regret total=%8.0f  mediu=%6.1f ms" % (rmw, tot, tot / n))
    print("  oracol             regret total=%8.0f  mediu=%6.1f ms" % (0, 0))
    print()

    print("== Selectoare (validare leave-one-condition-out) ==")
    res_nn = sc.evaluate_selector(cells, sc.nn_predict)
    report_eval("1-NN transparent (selector_core)", res_nn)
    results = [("always-zenoh", res_nn["always_zenoh_regret_mean"]),
               ("always-cyclonedds", res_nn["always_cyclonedds_regret_mean"]),
               ("selector 1-NN", res_nn["selector_regret_mean"])]

    sk = sklearn_predict_factory()
    if sk is not None:
        res_tree = sc.evaluate_selector(cells, sk)
        report_eval("DecisionTree max_depth=3 (sklearn)", res_tree)
        results.append(("selector tree", res_tree["selector_regret_mean"]))
    else:
        print("  [sklearn indisponibil -- doar 1-NN]")
    results.append(("oracol", 0.0))
    print()

    if objective == "lossaware":
        print("== Sensibilitate la deadline D (winner counts + regret mediu, cost ms) ==")
        for D in (200.0, 1000.0, 5000.0):
            cc = sc.build_cost_cells(rows, D)
            wins = {r: 0 for r in sc.RMWS}
            for k in cc:
                if len(cc[k]) >= 2:
                    wins[sc.cell_winner(cc[k])] += 1
            rs = sc.evaluate_selector(cc, sc.nn_predict)
            print("  D=%6.0f ms -> wins=%s | always-cyc=%7.1f always-zen=%7.1f selector1NN=%7.1f"
                  % (D, wins, rs["always_cyclonedds_regret_mean"],
                     rs["always_zenoh_regret_mean"], rs["selector_regret_mean"]))
        print()

    save_figure(results, os.path.join(HERE, "selector_regret.png"), objective)

    reps = sorted({r.get("rep", "") for r in rows})
    loss_vals = {r.get("loss_pct", "0") for r in rows}
    loss_real = loss_vals - {"0.0", "0", ""} != set()
    print("== Note oneste ==")
    if objective == "lossaware":
        print("  - obiectiv CONSTIENT DE PIERDERE: cost = (1-loss)*RTT_p95 + loss*D, D=%.0f ms." % penalty)
        if not loss_real:
            print("    ATENTIE: loss=0 in date -> costul COLAPSEAZA la RTT p95 (== control);")
            print("    are sens doar pe date cu pierdere reala (selector_dataset.csv din bridge).")
        print("    D e un knob de modelare (deadline-ul de control); vezi sensibilitatea la D mai sus.")
    else:
        print("  - obiectiv CONTROL (min RTT p95); ignora pierderea -- vezi --objective lossaware.")
    print("  - 'telemetrie = min timp misiune' indisponibil (fara timp de misiune in date)")
    print("    -- TODO: join cu stratul de misiune sar_swarm.")
    if loss_real:
        print("  - loss MASURAT in date (coloana loss_pct variaza) -- semnal de pierdere REAL.")
    else:
        print("  - loss_pct = 0 peste tot -> 'loss %' derivat din numele conditiei (set fara pierdere).")
    print("  - %d repetitii, loopback; comparatia autoritara cere HIL pe doua masini fizice."
          % len(reps))
    return 0


def save_figure(results, path, objective="control"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("  (matplotlib indisponibil -- fara figura)")
        return
    labels = [r[0] for r in results]
    vals = [r[1] for r in results]
    unit = "cost" if objective == "lossaware" else "RTT p95"
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, vals, color="#3a7")
    ax.set_ylabel("regret mediu %s [ms] (mai mic = mai bine)" % unit)
    ax.set_title("Selector vs reguli globale (LOCO; obiectiv %s)" % objective)
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    print("  figura salvata: %s" % path)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
