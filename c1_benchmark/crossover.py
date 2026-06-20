#!/usr/bin/env python3
"""crossover.py -- scoate REPRODUCTIBIL, din campaign_summary.csv, unde basculeaza
castigatorul (crossover) intre cele doua RMW si unde apare genunchiul (saltul brusc
de pierdere). Numere si etichete, nu interpretare -- concluzia stiintifica e a ta.

Schema asteptata (exact ca a ta):
  rmw,condition,rtt_p95_ms,transport_loss,mission_time_s,mission_completed,coverage_end

Utilizare:
  python3 crossover.py ~/c1_results_crossover/analysis/campaign_summary.csv
  python3 crossover.py --selftest          # valideaza logica pe date sintetice

Conventie: o conditie e considerata "egala" daca diferenta de p95 e sub un prag
absolut (zgomot sub-ms) SAU sub o toleranta relativa (implicit 10%) -- ca sa nu
declaram castigator o diferenta de 36 ms la 1100 ms.
"""
import csv
import sys

REL_TOL = 0.10      # diferente sub 10% = egalitate (marginal)
ABS_FLOOR_MS = 5.0  # diferente sub 5 ms = egalitate (zgomot)


# --------------------------------------------------------------------------
# LOGICA PURA (testabila fara fisier)
# --------------------------------------------------------------------------
def loss_pct(condition):
    """Procentul de pierdere netem din numele conditiei pe axa de pierdere.
    'ideal'->0; 'loss_25'->25; conditiile de latenta (lat...) -> None."""
    if condition == "ideal":
        return 0.0
    if condition.startswith("loss_") and not condition.endswith("_burst"):
        try:
            return float(condition.split("_")[1])
        except (IndexError, ValueError):
            return None
    return None


def winner(val_a, val_b, name_a, name_b,
           rel=REL_TOL, abs_floor=ABS_FLOOR_MS):
    """Cine are valoarea mai MICA (mai bine). 'egal' daca sub praguri."""
    diff = abs(val_a - val_b)
    if diff < abs_floor or diff < rel * max(val_a, val_b, 1e-9):
        return "egal"
    return name_a if val_a < val_b else name_b


def crossover_windows(rows_by_loss, names):
    """rows_by_loss: lista [(loss_pct, condition, p95_a, p95_b)] sortata crescator.
    Intoarce ferestrele unde castigatorul DECISIV pe p95 se schimba."""
    a, b = names
    windows = []
    prev = None
    prev_cond = None
    for _lp, cond, pa, pb in rows_by_loss:
        w = winner(pa, pb, a, b)
        if w == "egal":
            continue
        if prev is not None and w != prev:
            windows.append((prev_cond, prev, cond, w))
        prev, prev_cond = w, cond
    return windows


def knee_step(series):
    """series: lista [(loss_pct, condition, measured_loss)] sortata crescator.
    Intoarce (cond_de, cond_la, delta) pentru cel mai mare salt de pierdere."""
    best = None
    for i in range(len(series) - 1):
        d = series[i + 1][2] - series[i][2]
        if best is None or d > best[2]:
            best = (series[i][1], series[i + 1][1], d)
    return best


# --------------------------------------------------------------------------
# CITIRE + RAPORT
# --------------------------------------------------------------------------
def load(path):
    by_cond = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            by_cond.setdefault(r["condition"], {})[r["rmw"]] = {
                "p95": float(r["rtt_p95_ms"]),
                "loss": float(r["transport_loss"]),
                "mission": r.get("mission_completed", ""),
                "cov": float(r.get("coverage_end", "nan") or "nan"),
            }
    return by_cond


def report(path):
    by_cond = load(path)
    names = sorted({n for v in by_cond.values() for n in v})
    if len(names) != 2:
        sys.exit(f"astept exact 2 RMW, am gasit: {names}")
    a, b = names

    loss_conds = sorted(((loss_pct(c), c) for c in by_cond
                         if loss_pct(c) is not None))
    lat_conds = sorted(c for c in by_cond
                       if loss_pct(c) is None and not c.endswith("_burst"))

    print(f"== Comparatie {a} vs {b} ==\n")
    print(f"{'conditie':<14}{'pierd%':>7}  "
          f"{a+' p95':>14}{b+' p95':>14}  {'castiga p95':>14}  {'misiune '+b:>12}")
    rows_p95 = []
    for lp, c in loss_conds:
        da, db = by_cond[c][a], by_cond[c][b]
        w = winner(da["p95"], db["p95"], a, b)
        rows_p95.append((lp, c, da["p95"], db["p95"]))
        print(f"{c:<14}{lp:>6.0f}%  {da['p95']:>10.0f} ms{db['p95']:>10.0f} ms"
              f"  {w:>14}  {db['mission']:>12}")

    print("\n-- conditii cu latenta (in afara axei de pierdere) --")
    for c in lat_conds:
        da, db = by_cond[c][a], by_cond[c][b]
        wp = winner(da["p95"], db["p95"], a, b)
        wl = winner(da["loss"], db["loss"], a, b, abs_floor=0.02)
        print(f"{c:<14}        {da['p95']:>10.0f} ms{db['p95']:>10.0f} ms"
              f"  p95:{wp:<11} pierdere:{wl}")

    print("\n== CROSSOVER (p95) ==")
    wins = crossover_windows(rows_p95, (a, b))
    if not wins:
        print("  nicio basculare decisiva pe axa de pierdere.")
    for c_from, w_from, c_to, w_to in wins:
        print(f"  basculeaza intre {c_from} ({w_from}) si {c_to} ({w_to})")

    print("\n== GENUNCHI (saltul maxim de pierdere masurata) ==")
    for n in (a, b):
        ser = sorted((lp, c, by_cond[c][n]["loss"]) for lp, c in loss_conds)
        c_from, c_to, d = knee_step(ser)
        print(f"  {n:<11}: {c_from} -> {c_to}  (+{100*d:.1f} puncte pierdere)")

    # rafala: pierdere corelata, aceeasi medie ca geamanul independent
    burst = sorted((float(c.split("_")[1]), c) for c in by_cond
                   if c.endswith("_burst"))
    if burst:
        print("\n== RAFALA (corelat) vs INDEPENDENT, aceeasi medie ==")
        for lp, cb in burst:
            ci = cb[:-len("_burst")]
            for n in (a, b):
                ip = by_cond.get(ci, {}).get(n)
                bp = by_cond[cb][n]
                istr = (f"{ip['p95']:.0f} ms / {100*ip['loss']:.0f}%"
                        if ip else "lipsa geaman")
                print(f"  {lp:>4.0f}%  {n:<11}  indep: {istr:<18}"
                      f"rafala: {bp['p95']:.0f} ms / {100*bp['loss']:.0f}%")
        rows_b = [(lp, c, by_cond[c][a]["p95"], by_cond[c][b]["p95"])
                  for lp, c in burst]
        wb = crossover_windows(rows_b, (a, b))
        print("  crossover pe seria de rafala: "
              + (", ".join(f"{f}->{t} ({wt})" for f, _wf, t, wt in wb)
                 or "fara basculare"))
        print("  castigator p95, independent -> rafala:")
        for lp, cb in burst:
            ci = cb[:-len("_burst")]
            if ci in by_cond:
                wi = winner(by_cond[ci][a]["p95"], by_cond[ci][b]["p95"], a, b)
                wr = winner(by_cond[cb][a]["p95"], by_cond[cb][b]["p95"], a, b)
                print(f"    {lp:>4.0f}%: {wi} -> {wr}"
                      f"   {'<< FLIP' if wi != wr else ''}")


# --------------------------------------------------------------------------
def selftest():
    n = 0
    def ok(cond, msg):
        nonlocal n
        assert cond, msg
        n += 1
        print(f"  [ok] {msg}")

    ok(loss_pct("ideal") == 0.0 and loss_pct("loss_25") == 25.0
       and loss_pct("lat200_l15") is None, "loss_pct: parsare conditii")
    ok(loss_pct("loss_25_burst") is None,
       "loss_pct: rafala e in afara axei independente")
    ok(winner(900, 1769, "z", "d") == "z", "winner: mai mic castiga")
    ok(winner(1107, 1071, "d", "z") == "egal", "winner: sub 10% = egal")
    ok(winner(1.4, 1.7, "d", "z") == "egal", "winner: sub 5 ms = egal")

    # crossover sintetic: z castiga la 5/15/20, d la 25/30 -> fereastra 20..25
    rows = [(0, "ideal", 1.4, 1.7), (5, "loss_5", 140, 90),
            (15, "loss_15", 1107, 1071), (20, "loss_20", 1769, 910),
            (25, "loss_25", 2077, 4446), (30, "loss_30", 2321, 4819)]
    w = crossover_windows(rows, ("d", "z"))
    ok(len(w) == 1 and w[0][0] == "loss_20" and w[0][2] == "loss_25"
       and w[0][3] == "d", "crossover: fereastra loss_20..loss_25 spre d")

    # genunchi sintetic z: salt mare 20->25
    ser = [(0, "ideal", 0.0), (5, "loss_5", 0.0), (15, "loss_15", 0.077),
           (20, "loss_20", 0.094), (25, "loss_25", 0.373), (30, "loss_30", 0.453)]
    c_from, c_to, d = knee_step(ser)
    ok(c_from == "loss_20" and c_to == "loss_25" and round(d, 3) == 0.279,
       "genunchi: saltul maxim la loss_20->loss_25")
    print(f"\nTOATE TESTELE AU TRECUT: {n} verificari.")


def main():
    if "--selftest" in sys.argv:
        selftest()
        return
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    report(args[0])


if __name__ == "__main__":
    main()
