#!/usr/bin/env python3
"""verdict_misiune.py — verdictele M1–M4 din mission_summary.csv, in
propozitii gata de articol/slide. Tolerant la schema: detecteaza singur
coloanele (rmw / profil / repetitie / metrici numerice) si raporteaza ce
gaseste; daca o metrica lipseste, verdictul aferent e marcat N/A.

  python3 verdict_misiune.py ~/mission_results          # cauta analysis/mission_summary.csv
  python3 verdict_misiune.py cale/catre/mission_summary.csv
  python3 verdict_misiune.py --selftest                 # validare pe date sintetice
"""
import csv
import os
import sys
from collections import defaultdict


def _gaseste_csv(arg):
    if os.path.isfile(arg):
        return arg
    for c in (os.path.join(arg, "analysis", "mission_summary.csv"),
              os.path.join(arg, "mission_summary.csv")):
        if os.path.isfile(c):
            return c
    sys.exit(f"[eroare] nu gasesc mission_summary.csv pornind de la: {arg}")


def _col(rows, *candidati):
    """Prima coloana al carei nume contine unul dintre candidati."""
    chei = rows[0].keys()
    for cand in candidati:
        for k in chei:
            if cand in k.lower():
                return k
    return None


def _numerice(rows, exclude):
    num = []
    for k in rows[0].keys():
        if k in exclude:
            continue
        try:
            float(rows[0][k])
            num.append(k)
        except (TypeError, ValueError):
            pass
    return num


def medie(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def analizeaza(cale):
    rows = list(csv.DictReader(open(cale)))
    if not rows:
        sys.exit("[eroare] CSV gol")
    c_rmw = _col(rows, "rmw")
    c_prof = _col(rows, "profile", "profil", "scenario", "teren")
    c_rep = _col(rows, "rep", "seed")
    if not c_rmw:
        sys.exit("[eroare] nu gasesc coloana RMW")
    metrici = _numerice(rows, {c_rmw, c_prof, c_rep} - {None})

    # medii pe (rmw, profil)
    agg = defaultdict(lambda: defaultdict(list))
    for r in rows:
        cheie = (r[c_rmw].strip(), (r[c_prof].strip() if c_prof else "-"))
        for m in metrici:
            try:
                agg[cheie][m].append(float(r[m]))
            except (TypeError, ValueError):
                pass

    profile = sorted({k[1] for k in agg})
    rmws = sorted({k[0] for k in agg})
    print(f"\n== mediile pe celula (din {os.path.basename(cale)};"
          f" {len(rows)} rulari) ==")
    for m in metrici:
        print(f"\n  metrica: {m}")
        for p in profile:
            for r in rmws:
                v = medie(agg[(r, p)].get(m, []))
                if v is not None:
                    print(f"    {p:14s} {r:12s} {v:10.2f}")

    def delta(metr, p):
        a = medie(agg.get(("cyclonedds", p), {}).get(metr, []))
        b = medie(agg.get(("zenoh", p), {}).get(metr, []))
        if a in (None, 0) or b is None:
            return None
        return 100.0 * (b - a) / a, a, b

    def m_like(*subs):
        for m in metrici:
            if all(s in m.lower() for s in subs):
                return m
        return None

    print("\n== verdicte (propozitii de articol) ==")
    m_t90 = m_like("t90") or m_like("time") or m_like("timp")
    if m_t90:
        difs = []
        for p in profile:
            d = delta(m_t90, p)
            if d:
                pct, a, b = d
                semn = "mai rapid" if pct < 0 else "mai lent"
                print(f"  [M1/{p}] Zenoh {abs(pct):.0f}% {semn} pe {m_t90} "
                      f"({b:.1f} vs {a:.1f}) — fata de ordinele de marime de "
                      f"la transport: compresie confirmata"
                      if abs(pct) < 20 else
                      f"  [M1/{p}] ATENTIE: diferenta pe {m_t90} este "
                      f"{abs(pct):.0f}% ({b:.1f} vs {a:.1f}) — peste pragul "
                      f"de compresie; verifica rularile")
                difs.append((p, abs(pct)))
        if len(difs) == 2:
            (p1, d1), (p2, d2) = sorted(difs, key=lambda x: x[0])
            usor, greu = (d1, d2) if "urban" in p2 else (d2, d1)
            if greu - usor > 2.0:
                rezultat = "terenul greu AMPLIFICA diferenta (M2 confirmat)"
            elif usor - greu > 2.0:
                rezultat = "terenul greu REDUCE diferenta (M2 respins)"
            else:
                rezultat = "diferenta comparabila intre profiluri (M2 neutru)"
            print(f"  [M2] diferenta RMW pe {m_t90}: "
                  f"{p1} {d1:.0f}% vs {p2} {d2:.0f}% -> {rezultat}")
    else:
        print("  [M1/M2] N/A — nicio coloana T90/timp gasita")

    m_rtl = m_like("rtl")
    if m_rtl:
        for p in profile:
            d = delta(m_rtl, p)
            if d:
                pct, a, b = d
                rez = ("echivalent" if abs(b - a) < 1.0
                       else f"diferit ({b:.1f} vs {a:.1f})")
                print(f"  [M3/{p}] evenimente RTL: {rez} intre RMW-uri")
    else:
        print("  [M3] N/A — nicio coloana RTL gasita")

    m_done = m_like("complet") or m_like("done") or m_like("finaliz")
    if m_done:
        for p in profile:
            for r in rmws:
                v = medie(agg[(r, p)].get(m_done, []))
                if v is not None and v < 1.0:
                    print(f"  [M4/{p}] {r}: rata de finalizare {v:.2f} < 1 — "
                          f"esecuri pe acest profil")
        print(f"  [M4] profilurile fara mesaj de mai sus: toate misiunile "
              f"incheiate")
    else:
        print("  [M4] N/A — nicio coloana de finalizare gasita")
    print()


def selftest():
    import tempfile
    d = tempfile.mkdtemp()
    cale = os.path.join(d, "mission_summary.csv")
    with open(cale, "w") as f:
        f.write("rmw,profile,rep,t90_s,victims_found,rtl_events,completed\n")
        date = [("cyclonedds", "open_field", 100, 6, 1, 1),
                ("cyclonedds", "urban_rubble", 140, 5, 2, 1),
                ("zenoh", "open_field", 95, 6, 1, 1),
                ("zenoh", "urban_rubble", 115, 6, 2, 1)]
        for rmw, p, t, v, rtl, c in date:
            for rep in (1, 2):
                f.write(f"{rmw},{p},{rep},{t + rep},{v},{rtl},{c}\n")
    analizeaza(cale)
    print("[ok] selftest incheiat")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        selftest()
    else:
        analizeaza(_gaseste_csv(sys.argv[1] if len(sys.argv) > 1
                                else os.path.expanduser("~/mission_results")))
