#!/usr/bin/env python3
"""audit_campanie.py -- audit de COMPLETITUDINE al unei arhive de campanie (read-only,
pur Python, fara ROS, fara retea). NU modifica nimic si NU interpreteaza rezultate:
raspunde la o singura intrebare -- 'sunt datele intregi si coerente?', inainte de orice
analiza (quicklook_sil / make_tables_c2 / make_figures_c2).

Intrare: calea ARCH a arhivei, cu structura scrisa de run_campaign.py:
  <ARCH>/<rmw>/<conditie>/rep<N>/transport_p<P>.csv
  <ARCH>/<rmw>/<conditie>/rep<N>/transport_p<P>_summary.json
RMW-urile, conditiile si sarcinile utile NU sunt hardcodate: se DESCOPERA din arbore
(o arhiva poate avea p4096 si p65536, sau conditii redenumite manual, ex. *_INVALID).

Per repetitie se citesc patru fapte:
  dim_csv   -- dimensiunea CSV-ului in octeti
  n         -- campul 'n' din _summary.json (esantioane pastrate de bench_client)
  first_seq -- primul seq din CSV
  EMPTY     -- CSV cu ZERO randuri de date (doar antetul 'seq,rtt_ms', sau fisier gol)
CSV-ul contine DOAR esantioanele RECEPTIONATE (unul pe rand), deci n mic / EMPTY = pierdere
mare sau rulare ratata -- auditul semnaleaza, nu decide care din ele.

first_seq ASTEPTAT = 11: bench_client ignora primele 10 mesaje (incalzire), deci prima
secventa eligibila e 11. Sub pierdere mare, 12-14 e normal (primele eligibile s-au pierdut).
Un first_seq mult peste 11 = prefix de discovery / start decalat -- se raporteaza
INFORMATIV (coloana first_seq + nota 'seq'), NU ca eroare; verdictul ATENTIE il dau doar
problemele STRUCTURALE (fisiere lipsa, EMPTY, n=0, incoerenta summary-CSV, numar de
repetitii diferit de --reps).

Uz:
  python3 audit_campanie.py <ARCH> [--payload 4096] [--reps 10] [--first-seq-info 20]
  python3 audit_campanie.py --selftest
"""
import csv
import json
import os
import statistics
import sys

HEADER_ASTEPTAT = "seq,rtt_ms"
FIRST_SEQ_ASTEPTAT = 11          # bench_client: warm = 10 mesaje ignorate
FIRST_SEQ_INFO = 20              # peste acest prag first_seq se noteaza informativ


def _payload_din_nume(nume):
    """'transport_p4096.csv' -> 4096; None daca nu se potriveste tiparul."""
    if not (nume.startswith("transport_p") and nume.endswith(".csv")):
        return None
    try:
        return int(nume[len("transport_p"):-len(".csv")])
    except ValueError:
        return None


def scan_rep(rep_dir, payload):
    """Faptele unei repetitii pentru o sarcina utila. Nu arunca exceptii: orice
    problema devine un camp (csv_lipsa / json_lipsa / json_corupt)."""
    csv_path = os.path.join(rep_dir, "transport_p%d.csv" % payload)
    sj_path = os.path.join(rep_dir, "transport_p%d_summary.json" % payload)
    f = {"rep": os.path.basename(rep_dir), "csv_lipsa": not os.path.isfile(csv_path),
         "json_lipsa": not os.path.isfile(sj_path), "json_corupt": False,
         "dim_csv": None, "n": None, "n_randuri": None, "first_seq": None,
         "empty": False}
    if not f["csv_lipsa"]:
        f["dim_csv"] = os.path.getsize(csv_path)
        randuri = 0
        with open(csv_path, newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    seq = int(row["seq"])
                except (KeyError, ValueError, TypeError):
                    continue
                randuri += 1
                if f["first_seq"] is None:
                    f["first_seq"] = seq
        f["n_randuri"] = randuri
        f["empty"] = (randuri == 0)
    if not f["json_lipsa"]:
        try:
            with open(sj_path) as fh:
                d = json.load(fh)
            f["n"] = d.get("n")
        except (ValueError, OSError):
            f["json_corupt"] = True
    return f


def _reps_din(cond_dir):
    """Subdirectoarele rep* ale unei conditii, in ordine NUMERICA (rep2 < rep10)."""
    if not os.path.isdir(cond_dir):
        return []
    reps = [d for d in os.listdir(cond_dir)
            if d.startswith("rep") and os.path.isdir(os.path.join(cond_dir, d))]
    def cheie(d):
        try:
            return (0, int(d[3:]))
        except ValueError:
            return (1, 0)
    return [os.path.join(cond_dir, d) for d in sorted(reps, key=cheie)]


def descopera(root):
    """Descopera (rmw, conditie, payload) din arbore. Intoarce lista sortata."""
    gasit = set()
    if not os.path.isdir(root):
        return []
    for rmw in sorted(os.listdir(root)):
        rmw_dir = os.path.join(root, rmw)
        if not os.path.isdir(rmw_dir):
            continue
        for cond in sorted(os.listdir(rmw_dir)):
            for rep_dir in _reps_din(os.path.join(rmw_dir, cond)):
                for nume in os.listdir(rep_dir):
                    p = _payload_din_nume(nume)
                    if p is not None:
                        gasit.add((rmw, cond, p))
    return sorted(gasit, key=lambda t: (t[1], t[0], t[2]))


def scan_celula(root, rmw, cond, payload, reps_asteptate=None,
                first_seq_info=FIRST_SEQ_INFO):
    """Agrega o celula (rmw x conditie x payload) peste repetitii + verdict."""
    reps = [scan_rep(rd, payload) for rd in _reps_din(os.path.join(root, rmw, cond))]
    reps = [r for r in reps if not (r["csv_lipsa"] and r["json_lipsa"])]
    ns = [r["n"] for r in reps if isinstance(r["n"], int)]
    fs = [r["first_seq"] for r in reps if r["first_seq"] is not None]
    n0 = sum(1 for r in reps if r["n"] == 0 or r["n_randuri"] == 0)
    empty = sum(1 for r in reps if r["empty"])
    lipsa = sum(1 for r in reps if r["csv_lipsa"] or r["json_lipsa"])
    corupt = sum(1 for r in reps if r["json_corupt"])
    # incoerenta: 'n' din summary != randurile efective din CSV
    mismatch = sum(1 for r in reps
                   if isinstance(r["n"], int) and isinstance(r["n_randuri"], int)
                   and r["n"] != r["n_randuri"])
    note = []
    if lipsa:
        note.append("lipsa")
    if corupt:
        note.append("corupt")
    if empty:
        note.append("empty")
    if n0:
        note.append("n0")
    if mismatch:
        note.append("mismatch")
    if reps_asteptate is not None and len(reps) != reps_asteptate:
        note.append("reps")
    verdict = "OK" if not note else "ATENTIE"
    # first_seq: informativ, NU schimba verdictul
    info = []
    if fs and min(fs) < FIRST_SEQ_ASTEPTAT:
        info.append("seq<%d" % FIRST_SEQ_ASTEPTAT)
    if fs and max(fs) > first_seq_info:
        info.append("seq>%d" % first_seq_info)
    return {
        "rmw": rmw, "cond": cond, "payload": payload,
        "reps": len(reps),
        "n_min": min(ns) if ns else None,
        "n_med": statistics.median(ns) if ns else None,
        "n_max": max(ns) if ns else None,
        "n0": n0, "empty": empty, "lipsa": lipsa, "corupt": corupt,
        "mismatch": mismatch,
        "first_seq_min": min(fs) if fs else None,
        "first_seq_max": max(fs) if fs else None,
        "dim_csv_min": min([r["dim_csv"] for r in reps if r["dim_csv"] is not None],
                           default=None),
        "dim_csv_max": max([r["dim_csv"] for r in reps if r["dim_csv"] is not None],
                           default=None),
        "verdict": verdict, "note": note, "info": info,
    }


def audit(root, payload=None, reps_asteptate=None, first_seq_info=FIRST_SEQ_INFO):
    """Auditul intregii arhive. payload=None -> toate sarcinile utile gasite."""
    celule = [c for c in descopera(root) if payload is None or c[2] == payload]
    return [scan_celula(root, rmw, cond, p, reps_asteptate, first_seq_info)
            for rmw, cond, p in celule]


def _f(v, nd=0):
    if v is None:
        return "-"
    return ("%%.%df" % nd) % v if isinstance(v, float) else str(v)


def tipareste(rows, root, reps_asteptate=None):
    """Tabelul ASCII + legenda + rezumatul final."""
    print("== AUDIT COMPLETITUDINE: %s ==" % root)
    if not rows:
        print("(nicio celula <rmw>/<conditie>/rep*/transport_p*.csv gasita)")
        return
    cap = ("%-22s %-11s %6s %5s %7s %8s %7s %6s %6s %-11s %-9s %s"
           % ("conditie", "rmw", "payload", "reps", "n_min", "n_med", "n_max",
              "n0", "empty", "first_seq", "verdict", "note"))
    print(cap)
    print("-" * len(cap))
    for r in rows:
        fsr = "-"
        if r["first_seq_min"] is not None:
            fsr = ("%d" % r["first_seq_min"] if r["first_seq_min"] == r["first_seq_max"]
                   else "%d..%d" % (r["first_seq_min"], r["first_seq_max"]))
        note = ",".join(r["note"] + ["(%s)" % i for i in r["info"]]) or "-"
        print("%-22s %-11s %6d %5d %7s %8s %7s %6s %6d %-11s %-9s %s" % (
            r["cond"], r["rmw"], r["payload"], r["reps"],
            _f(r["n_min"]), _f(r["n_med"], 1), _f(r["n_max"]),
            "%d/%d" % (r["n0"], r["reps"]), r["empty"], fsr, r["verdict"], note))
    atentie = [r for r in rows if r["verdict"] != "OK"]
    print("-" * len(cap))
    print("total %d celule: %d OK, %d ATENTIE" % (len(rows), len(rows) - len(atentie),
                                                  len(atentie)))
    print("\nLEGENDA")
    print("  n         = campul 'n' din _summary.json; n_med = MEDIANA peste repetitii")
    print("  n0=k/N    = repetitii cu n=0 (sau CSV fara randuri) din N gasite")
    print("  empty     = CSV-uri cu doar antetul '%s'" % HEADER_ASTEPTAT)
    print("  first_seq = primul seq din CSV; ASTEPTAT %d (bench_client ignora 10 de "
          "incalzire)" % FIRST_SEQ_ASTEPTAT)
    print("  ATENTIE doar pe probleme STRUCTURALE:")
    print("    lipsa    = CSV sau _summary.json lipsa intr-o repetitie")
    print("    corupt   = _summary.json ilizibil (JSON invalid)")
    print("    empty    = cel putin un CSV fara randuri de date")
    print("    n0       = cel putin o repetitie cu n=0")
    print("    mismatch = 'n' din summary != numarul de randuri din CSV")
    if reps_asteptate is not None:
        print("    reps     = numar de repetitii != %d (--reps)" % reps_asteptate)
    print("  (seq<%d) / (seq>%d) = nota INFORMATIVA pe first_seq (prefix de discovery /"
          % (FIRST_SEQ_ASTEPTAT, FIRST_SEQ_INFO))
    print("    start decalat); NU schimba verdictul.")


def _selftest():
    """Fixture TEMPORAR (nicio data reala atinsa): 5 celule construite ca sa loveasca
    fiecare regula -- OK curat, EMPTY, n=0, mismatch, fisier lipsa, first_seq mare."""
    import shutil
    import tempfile
    root = tempfile.mkdtemp(prefix="audit_selftest_")
    try:
        def rep(rmw, cond, n_rep, randuri, n_summary=None, fara_json=False,
                fara_csv=False, first=11):
            rd = os.path.join(root, rmw, cond, "rep%d" % n_rep)
            os.makedirs(rd)
            if not fara_csv:
                with open(os.path.join(rd, "transport_p4096.csv"), "w") as f:
                    f.write(HEADER_ASTEPTAT + "\n")
                    for i in range(randuri):
                        f.write("%d,%.3f\n" % (first + i, 1.0 + i))
            if not fara_json:
                n = randuri if n_summary is None else n_summary
                with open(os.path.join(rd, "transport_p4096_summary.json"), "w") as f:
                    json.dump({"n": n, "sent": 989, "received": n}, f)

        # 1. celula curata: 3 rep x 5 randuri, first_seq 11
        for k in (1, 2, 3):
            rep("cyclonedds", "ideal", k, 5)
        # 2. o repetitie EMPTY (doar antet) + n=0 in summary
        rep("cyclonedds", "ge_15_8", 1, 5)
        rep("cyclonedds", "ge_15_8", 2, 0, n_summary=0)
        # 3. mismatch: summary spune 9, CSV are 4 randuri
        rep("zenoh", "bern_15", 1, 4, n_summary=9)
        # 4. fisiere lipsa: repetitie fara _summary.json
        rep("zenoh", "ideal", 1, 5)
        rep("zenoh", "ideal", 2, 5, fara_json=True)
        # 5. first_seq mare (prefix de discovery) -- INFORMATIV, ramane OK
        rep("zenoh", "ge_5_3", 1, 5, first=137)

        # descoperirea nu hardcodeaza nimic
        celule = descopera(root)
        assert len(celule) == 5, celule
        assert ("cyclonedds", "ideal", 4096) in celule, celule

        R = {(r["rmw"], r["cond"]): r for r in audit(root, payload=4096)}

        c = R[("cyclonedds", "ideal")]
        assert c["reps"] == 3 and c["verdict"] == "OK", c
        assert (c["n_min"], c["n_med"], c["n_max"]) == (5, 5, 5), c
        assert c["n0"] == 0 and c["empty"] == 0, c
        assert c["first_seq_min"] == 11 and c["first_seq_max"] == 11, c

        e = R[("cyclonedds", "ge_15_8")]
        assert e["verdict"] == "ATENTIE" and e["empty"] == 1 and e["n0"] == 1, e
        assert "empty" in e["note"] and "n0" in e["note"], e
        assert (e["n_min"], e["n_max"]) == (0, 5), e
        assert e["n_med"] == 2.5, e            # mediana peste [0, 5]

        m = R[("zenoh", "bern_15")]
        assert m["verdict"] == "ATENTIE" and m["mismatch"] == 1, m
        assert "mismatch" in m["note"], m

        l = R[("zenoh", "ideal")]
        assert l["verdict"] == "ATENTIE" and l["lipsa"] == 1, l
        assert l["reps"] == 2, l               # repetitia fara json e tot numarata

        s = R[("zenoh", "ge_5_3")]
        assert s["verdict"] == "OK", s         # first_seq mare NU e eroare
        assert s["info"] == ["seq>%d" % FIRST_SEQ_INFO], s
        assert s["first_seq_min"] == 137, s

        # --reps: 3 asteptate -> celulele cu 1-2 repetitii capata nota 'reps'
        R3 = {(r["rmw"], r["cond"]): r for r in audit(root, 4096, reps_asteptate=3)}
        assert R3[("cyclonedds", "ideal")]["verdict"] == "OK", R3
        assert "reps" in R3[("zenoh", "bern_15")]["note"], R3

        # arhiva inexistenta / goala -> lista goala, fara exceptie
        assert audit(os.path.join(root, "nu_exista")) == []
        print("SELFTEST audit_campanie OK (18 verificari, fixture temporar).")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if argv[0] == "--selftest":
        _selftest()
        return 0
    root = os.path.expanduser(argv[0])
    payload, reps_asteptate, fs_info = None, None, FIRST_SEQ_INFO
    rest = argv[1:]
    i = 0
    while i < len(rest):
        if rest[i] == "--payload" and i + 1 < len(rest):
            payload = int(rest[i + 1]); i += 2
        elif rest[i] == "--reps" and i + 1 < len(rest):
            reps_asteptate = int(rest[i + 1]); i += 2
        elif rest[i] == "--first-seq-info" and i + 1 < len(rest):
            fs_info = int(rest[i + 1]); i += 2
        else:
            print("argument necunoscut: %s" % rest[i])
            return 2
    if not os.path.isdir(root):
        print("cale inexistenta: %s" % root)
        return 2
    rows = audit(root, payload, reps_asteptate, fs_info)
    tipareste(rows, root, reps_asteptate)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
