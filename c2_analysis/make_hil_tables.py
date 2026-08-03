#!/usr/bin/env python3
"""make_hil_tables.py -- tabelele CANONICE ale campaniei HIL (Wi-Fi, doua masini).

READ-ONLY pe date: nu scrie NIMIC in arhivele de campanie (sunt sigilate a-w). Singurul
loc in care scrie e ~/DATE_CAMPANIE/ANALIZA_C2/ (o creeaza daca lipseste).

DISCIPLINA STATISTICA (Wuensch): pe HIL exista rulari in care NIMIC nu a ajuns (n=0).
O medie peste toate rularile ar amesteca doua populatii diferite (livrare partiala vs
esec total) si ar produce un numar care nu descrie niciuna. De aceea:
  - fractia de ESEC se raporteaza SEPARAT, ca n0=k/N (k rulari cu n=0 din N);
  - mediana/min/max se calculeaza DOAR pe rularile SUPRAVIETUITOARE (n>0), si sunt
    explicit statistici CONDITIONATE pe supravietuire;
  - se foloseste MEDIANA, nu media: pe N=10 cu distributii puternic asimetrice
    (bimodale) mediana descrie 'rularea tipica', media nu descrie nimic.
Cine vrea numarul neconditionat il poate reface: livrare_efectiva ~ (1-n0/N) * mediana.

first_seq (primul seq din CSV) e raportat ca PROXY pentru prefixul de discovery:
bench_client ignora 10 mesaje de incalzire, deci prima secventa eligibila e 11; cu cat
first_seq e mai mare, cu atat sesiunea a avut nevoie de mai mult timp ca sa livreze
primul pachet. NU e o metrica de pierdere, e o metrica de PORNIRE.

Directoarele-proba (sufixe *_INVALID, *_ECOUMORT) sunt EXCLUSE explicit si listate ca
atare in iesire -- nu dispar in tacere.

Iesiri in ANALIZA_C2/:
  tabel_hil_4k.md / .tex     -- grila 4KB (C2_HIL_WIFI_20260801)
  tabel_hil_64k.md / .tex    -- sonda 64KB (C2_HIL_WIFI64_20260803)
  tabel_sil_vs_hil.md        -- delte pe conditiile COMUNE (SIL descoperit pe disc)
Fisierele .tex sunt documente COMPLETE, compilabile cu 'article' (tabular simplu, fara
booktabs -- pachetul poate lipsi din containerul de build).

Uz:
  python3 make_hil_tables.py [ARH_4K] [ARH_64K] [--out DIR]
  python3 make_hil_tables.py --selftest
"""
import csv
import glob
import json
import os
import statistics
import sys

HOME = os.path.expanduser("~")
DATE = os.path.join(HOME, "DATE_CAMPANIE")
OUT_DEFAULT = os.path.join(DATE, "ANALIZA_C2")
ARH_4K_DEFAULT = os.path.join(DATE, "C2_HIL_WIFI_20260801")
ARH_64K_DEFAULT = os.path.join(DATE, "C2_HIL_WIFI64_20260803")
PAY_4K, PAY_64K = 4096, 65536
RMWS = ("cyclonedds", "zenoh")
ETICHETA = {"cyclonedds": "cdds", "zenoh": "zenoh"}
EXCLUSE_SUFIXE = ("_INVALID", "_ECOUMORT")
FIRST_SEQ_ASTEPTAT = 11

# ordinea canonica in tabele (grila L x B, apoi extra); necunoscutele merg la coada
ORDINE = ["ideal",
          "bern_5", "ge_5_3", "ge_5_8",
          "bern_15", "ge_15_3", "ge_15_8",
          "bern_30", "ge_30_3", "ge_30_8",
          "lat200_jit50_ge_15_8"]


def e_proba(nume):
    """Director-proba (rulare invalidata manual), exclus din tabelele canonice."""
    return any(nume.endswith(s) for s in EXCLUSE_SUFIXE)


def descopera_conditii(root, rmw):
    """(conditii_valide, proba_excluse) din <root>/<rmw>/, in ordinea canonica."""
    d = os.path.join(root, rmw)
    if not os.path.isdir(d):
        return [], []
    toate = sorted(n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n)))
    valide = [n for n in toate if not e_proba(n)]
    excluse = [n for n in toate if e_proba(n)]
    valide.sort(key=lambda n: (ORDINE.index(n) if n in ORDINE else len(ORDINE), n))
    return valide, excluse


def descopera_arhiva(tipar):
    """Gaseste pe disc arhiva care se potriveste cu tiparul (ex. 'C2_SIL_*').
    NU ghiceste nume: daca nu exista exact una, spune ce a gasit si intoarce None."""
    gasite = sorted(p for p in glob.glob(os.path.join(DATE, tipar)) if os.path.isdir(p))
    if len(gasite) == 1:
        return gasite[0]
    return None


def citeste_rep(rep_dir, payload):
    """Faptele unei repetitii. Nu arunca exceptii; problemele devin campuri."""
    cf = os.path.join(rep_dir, "transport_p%d.csv" % payload)
    sj = os.path.join(rep_dir, "transport_p%d_summary.json" % payload)
    f = {"rep": os.path.basename(rep_dir), "n": None, "sent": None, "received": None,
         "first_seq": None, "randuri": None, "lipsa": False, "corupt": False}
    if not os.path.isfile(cf) or not os.path.isfile(sj):
        f["lipsa"] = True
        return f
    try:
        with open(sj) as fh:
            d = json.load(fh)
        f["n"] = d.get("n")
        f["sent"] = d.get("sent")
        f["received"] = d.get("received")
    except (ValueError, OSError):
        f["corupt"] = True
        return f
    randuri = 0
    with open(cf, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                seq = int(row["seq"])
            except (KeyError, ValueError, TypeError):
                continue
            randuri += 1
            if f["first_seq"] is None:
                f["first_seq"] = seq
    f["randuri"] = randuri
    return f


def anomalii_rep(f, cond, rmw):
    """Anomalii MECANICE (nu stiintifice) ale unei repetitii."""
    out = []
    unde = "%s/%s/%s" % (rmw, cond, f["rep"])
    if f["lipsa"]:
        out.append((unde, "fisiere lipsa (CSV sau _summary.json)"))
        return out
    if f["corupt"]:
        out.append((unde, "_summary.json ilizibil"))
        return out
    if isinstance(f["n"], int) and isinstance(f["randuri"], int) and f["n"] != f["randuri"]:
        out.append((unde, "mismatch summary-vs-CSV: n=%s, randuri CSV=%s"
                    % (f["n"], f["randuri"])))
    if f["first_seq"] is not None and f["first_seq"] < FIRST_SEQ_ASTEPTAT:
        out.append((unde, "first_seq=%d < %d (incalzirea ar fi trebuit ignorata)"
                    % (f["first_seq"], FIRST_SEQ_ASTEPTAT)))
    if isinstance(f["n"], int) and isinstance(f["sent"], int) and f["n"] > f["sent"]:
        out.append((unde, "n=%d > sent=%d (imposibil)" % (f["n"], f["sent"])))
    return out


def _reps(root, rmw, cond):
    d = os.path.join(root, rmw, cond)
    if not os.path.isdir(d):
        return []
    nume = [x for x in os.listdir(d) if x.startswith("rep")
            and os.path.isdir(os.path.join(d, x))]

    def cheie(x):
        try:
            return (0, int(x[3:]))
        except ValueError:
            return (1, 0)
    return [os.path.join(d, x) for x in sorted(nume, key=cheie)]


def celula(root, rmw, cond, payload):
    """Agrega o celula (conditie x RMW) cu disciplina supravietuitorilor."""
    reps = [citeste_rep(rd, payload) for rd in _reps(root, rmw, cond)]
    reps = [f for f in reps if not f["lipsa"]]
    N = len(reps)
    morti = [f for f in reps if not f["n"]]                 # n == 0 sau None
    vii = [f for f in reps if f["n"]]
    liv = [100.0 * f["received"] / f["sent"] for f in vii
           if f.get("sent")]                                # livrare % pe supravietuitori
    fs = [f["first_seq"] for f in vii if f["first_seq"] is not None]
    anom = []
    for f in reps:
        anom += anomalii_rep(f, cond, rmw)
    return {
        "cond": cond, "rmw": rmw, "N": N, "n0": len(morti), "vii": len(vii),
        "liv_med": statistics.median(liv) if liv else None,
        "liv_min": min(liv) if liv else None,
        "liv_max": max(liv) if liv else None,
        "n_med": statistics.median([f["n"] for f in vii]) if vii else None,
        "first_seq_med": statistics.median(fs) if fs else None,
        "anomalii": anom,
    }


def tabel(root, payload):
    """Toate celulele unei arhive + directoarele-proba excluse."""
    randuri, excluse = [], {}
    for rmw in RMWS:
        conds, ex = descopera_conditii(root, rmw)
        if ex:
            excluse[rmw] = ex
        for c in conds:
            randuri.append(celula(root, rmw, c, payload))
    return randuri, excluse


# --------------------------------------------------------------- formatare (pura)
def _f(v, nd=1):
    return "-" if v is None else ("%%.%df" % nd) % v


def _fi(v):
    return "-" if v is None else "%d" % round(v)


CAP = ["conditie", "RMW", "N", "n0", "supr.", "livrare% med", "min", "max", "first_seq med"]


def _celule_text(r):
    return [r["cond"], ETICHETA[r["rmw"]], "%d" % r["N"],
            "%d/%d" % (r["n0"], r["N"]), "%d" % r["vii"],
            _f(r["liv_med"]), _f(r["liv_min"]), _f(r["liv_max"]), _fi(r["first_seq_med"])]


def md_tabel(randuri, titlu, excluse=None, nota=""):
    """Tabel markdown; statisticile sunt CONDITIONATE pe supravietuitori."""
    out = ["## %s" % titlu, ""]
    if nota:
        out += [nota, ""]
    out.append("| " + " | ".join(CAP) + " |")
    out.append("|" + "|".join(["---"] * len(CAP)) + "|")
    for r in randuri:
        out.append("| " + " | ".join(_celule_text(r)) + " |")
    out.append("")
    out.append("n0=k/N: rulari cu ZERO esantioane livrate. Coloanele livrare si first_seq "
               "(mediana, min, max) sunt calculate DOAR pe cele 'supr.' rulari "
               "supravietuitoare (n>0).")
    if excluse:
        for rmw, ex in sorted(excluse.items()):
            out.append("")
            out.append("EXCLUS (director-proba, %s): %s" % (rmw, ", ".join(ex)))
    out.append("")
    return "\n".join(out)


def tex_esc(s):
    return s.replace("_", r"\_").replace("%", r"\%")


def tex_tabel(randuri, titlu, nota=""):
    """Document LaTeX COMPLET (article), tabular simplu, FARA booktabs."""
    cap = ["conditie", "RMW", "N", "$n_0$", "supr.", "livrare\\% med", "min", "max",
           "first\\_seq med"]
    out = [r"\documentclass[10pt]{article}",
           r"\usepackage[margin=2cm]{geometry}",
           r"\begin{document}",
           r"\begin{table}[h]", r"\centering",
           r"\caption{%s}" % tex_esc(titlu),
           r"\begin{tabular}{llrrrrrrr}", r"\hline",
           " & ".join(cap) + r" \\", r"\hline"]
    for r in randuri:
        out.append(" & ".join(tex_esc(x) for x in _celule_text(r)) + r" \\")
    out += [r"\hline", r"\end{tabular}"]
    if nota:
        out.append(r"\\[2pt] \footnotesize %s" % tex_esc(nota))
    out += [r"\end{table}", r"\end{document}", ""]
    return "\n".join(out)


def md_sil_vs_hil(perechi, titlu):
    """perechi: lista de (cond, rmw, celula_sil, celula_hil). Delta = HIL - SIL."""
    cap = ["conditie", "RMW", "SIL n0", "SIL livr% med", "HIL n0", "HIL livr% med",
           "delta livr% (HIL-SIL)", "delta first_seq"]
    out = ["## %s" % titlu, "",
           "| " + " | ".join(cap) + " |",
           "|" + "|".join(["---"] * len(cap)) + "|"]
    for cond, rmw, s, h in perechi:
        d = (None if (s["liv_med"] is None or h["liv_med"] is None)
             else h["liv_med"] - s["liv_med"])
        dfs = (None if (s["first_seq_med"] is None or h["first_seq_med"] is None)
               else h["first_seq_med"] - s["first_seq_med"])
        out.append("| " + " | ".join([
            cond, ETICHETA[rmw], "%d/%d" % (s["n0"], s["N"]), _f(s["liv_med"]),
            "%d/%d" % (h["n0"], h["N"]), _f(h["liv_med"]),
            ("%+.1f" % d) if d is not None else "-",
            ("%+d" % round(dfs)) if dfs is not None else "-"]) + " |")
    out += ["", "Delta pozitiv = HIL livreaza MAI MULT decat SIL. Medianele sunt "
            "conditionate pe supravietuitori, deci se citesc IMPREUNA cu n0.", ""]
    return "\n".join(out)


def comune(root_sil, root_hil, payload):
    """Perechile (cond, rmw, celula_sil, celula_hil) pe conditiile prezente in AMBELE."""
    perechi = []
    for rmw in RMWS:
        cs, _ = descopera_conditii(root_sil, rmw)
        ch, _ = descopera_conditii(root_hil, rmw)
        for c in [x for x in cs if x in ch]:
            perechi.append((c, rmw, celula(root_sil, rmw, c, payload),
                            celula(root_hil, rmw, c, payload)))
    perechi.sort(key=lambda t: (ORDINE.index(t[0]) if t[0] in ORDINE else len(ORDINE),
                                t[0], t[1]))
    return perechi


def toate_anomaliile(randuri):
    out = []
    for r in randuri:
        out += r["anomalii"]
    return out


# ------------------------------------------------------------------------ selftest
def _selftest():
    """Fixture TEMPORAR in /tmp (nicio data reala atinsa): o celula cu 2 morti din 5,
    un director-proba care trebuie EXCLUS, si trei anomalii injectate."""
    import shutil
    import tempfile
    root = tempfile.mkdtemp(prefix="hil_tabele_selftest_")
    try:
        def rep(rmw, cond, k, seqs, sent=989, n=None, mism=False):
            rd = os.path.join(root, rmw, cond, "rep%d" % k)
            os.makedirs(rd)
            with open(os.path.join(rd, "transport_p4096.csv"), "w") as f:
                f.write("seq,rtt_ms\n")
                for s in seqs:
                    f.write("%d,1.5\n" % s)
            nn = (len(seqs) if n is None else n)
            if mism:
                nn = len(seqs) + 7
            with open(os.path.join(rd, "transport_p4096_summary.json"), "w") as f:
                json.dump({"n": nn, "sent": sent, "received": nn}, f)

        # celula cu 5 rulari: 2 moarte, 3 vii cu livrari 10%, 20%, 60% (din sent=100)
        rep("zenoh", "ge_15_8", 1, list(range(11, 21)), sent=100)      # 10 -> 10%
        rep("zenoh", "ge_15_8", 2, list(range(11, 31)), sent=100)      # 20 -> 20%
        rep("zenoh", "ge_15_8", 3, list(range(11, 71)), sent=100)      # 60 -> 60%
        rep("zenoh", "ge_15_8", 4, [], sent=100)                       # mort
        rep("zenoh", "ge_15_8", 5, [], sent=100)                       # mort
        # director-proba: trebuie EXCLUS complet
        rep("zenoh", "bern_5_MIXT_INVALID", 1, list(range(11, 100)), sent=100)
        # anomalii injectate, fiecare in alta repetitie
        rep("cyclonedds", "ideal", 1, list(range(11, 21)), sent=100, mism=True)
        rep("cyclonedds", "ideal", 2, list(range(3, 13)), sent=100)     # first_seq=3 < 11
        rep("cyclonedds", "ideal", 3, list(range(11, 21)), sent=5)      # n=10 > sent=5

        valide, excluse = descopera_conditii(root, "zenoh")
        assert valide == ["ge_15_8"], valide
        assert excluse == ["bern_5_MIXT_INVALID"], excluse
        assert e_proba("x_ECOUMORT") and e_proba("y_INVALID") and not e_proba("ge_15_8")

        c = celula(root, "zenoh", "ge_15_8", 4096)
        assert c["N"] == 5 and c["n0"] == 2 and c["vii"] == 3, c
        assert c["liv_med"] == 20.0, c          # mediana pe SUPRAVIETUITORI (10,20,60)
        assert c["liv_min"] == 10.0 and c["liv_max"] == 60.0, c
        assert c["first_seq_med"] == 11, c
        assert c["n_med"] == 20, c
        # mortii NU trag mediana in jos (ar fi fost 10.0 cu zerourile incluse)
        assert statistics.median([0, 0, 10, 20, 60]) == 10.0

        randuri, ex = tabel(root, 4096)
        assert len(randuri) == 2, randuri          # ideal (cdds) + ge_15_8 (zenoh)
        assert ex == {"zenoh": ["bern_5_MIXT_INVALID"]}, ex
        anom = toate_anomaliile(randuri)
        texte = " ".join(a[1] for a in anom)
        assert "mismatch summary-vs-CSV" in texte, anom
        assert "first_seq=3" in texte, anom
        assert "n=10 > sent=5" in texte, anom
        assert len(anom) == 3, anom

        # markdown: antet, randuri, nota de excludere
        md = md_tabel(randuri, "T", ex)
        assert "| conditie | RMW |" in md and "| ge_15_8 | zenoh |" in md, md
        assert "2/5" in md and "20.0" in md, md
        assert "EXCLUS (director-proba, zenoh): bern_5_MIXT_INVALID" in md, md
        assert "bern_5_MIXT_INVALID" not in md.split("EXCLUS")[0], "proba a intrat in tabel"
        # latex: document complet, fara booktabs, underscore escapat
        tx = tex_tabel(randuri, "T")
        assert tx.startswith(r"\documentclass") and r"\end{document}" in tx, tx[:80]
        assert "booktabs" not in tx and r"\toprule" not in tx, tx
        assert r"ge\_15\_8" in tx and "ge_15_8" not in tx.replace(r"ge\_15\_8", ""), tx
        assert tx.count(r"\hline") == 3, tx
        # sil vs hil: delta = HIL - SIL
        s = dict(celula(root, "zenoh", "ge_15_8", 4096))
        h = dict(s); h["liv_med"] = 50.0; h["first_seq_med"] = 40
        m = md_sil_vs_hil([("ge_15_8", "zenoh", s, h)], "D")
        assert "+30.0" in m and "+29" in m, m
        print("SELFTEST make_hil_tables OK (24 verificari, fixture temporar in /tmp).")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def scrie(cale, text):
    with open(cale, "w") as f:
        f.write(text)
    print("  scris %s (%d octeti)" % (cale, len(text.encode())))


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    poz = [a for a in argv if not a.startswith("--")]
    out = OUT_DEFAULT
    if "--out" in argv:
        out = os.path.expanduser(argv[argv.index("--out") + 1])
    arh4 = os.path.expanduser(poz[0]) if len(poz) > 0 else ARH_4K_DEFAULT
    arh64 = os.path.expanduser(poz[1]) if len(poz) > 1 else ARH_64K_DEFAULT
    for a in (arh4, arh64):
        if not os.path.isdir(a):
            print("arhiva inexistenta: %s" % a)
            return 2
    os.makedirs(out, exist_ok=True)
    print("ARH 4K : %s" % arh4)
    print("ARH 64K: %s" % arh64)
    print("iesire : %s" % out)

    nota4 = ("Campanie HIL Wi-Fi, sarcina utila 4096 B, N=10 repetitii/celula. "
             "Statistici CONDITIONATE pe rularile supravietuitoare (n>0); "
             "fractia de esec e raportata separat ca n0=k/N.")
    r4, ex4 = tabel(arh4, PAY_4K)
    scrie(os.path.join(out, "tabel_hil_4k.md"),
          md_tabel(r4, "HIL Wi-Fi 4KB -- %s" % os.path.basename(arh4), ex4, nota4))
    scrie(os.path.join(out, "tabel_hil_4k.tex"),
          tex_tabel(r4, "HIL Wi-Fi 4KB -- %s" % os.path.basename(arh4), nota4))

    nota64 = ("Sonda HIL 64KB (65536 B), N=10 repetitii/celula. Aceleasi conventii "
              "ca la 4KB: mediane pe supravietuitori, esecul separat in n0.")
    r64, ex64 = tabel(arh64, PAY_64K)
    scrie(os.path.join(out, "tabel_hil_64k.md"),
          md_tabel(r64, "HIL Wi-Fi 64KB -- %s" % os.path.basename(arh64), ex64, nota64))
    scrie(os.path.join(out, "tabel_hil_64k.tex"),
          tex_tabel(r64, "HIL Wi-Fi 64KB -- %s" % os.path.basename(arh64), nota64))

    # SIL descoperit pe disc (nu ghicit)
    sil4 = descopera_arhiva("C2_SIL_*")
    sil64 = descopera_arhiva("C2_SIL64*")
    bucati = ["# SIL vs HIL -- conditii comune", "",
              "SIL 4KB : %s" % (sil4 or "NEGASIT"),
              "SIL 64KB: %s" % (sil64 or "NEGASIT"),
              "HIL 4KB : %s" % arh4,
              "HIL 64KB: %s" % arh64, ""]
    if sil4:
        bucati.append(md_sil_vs_hil(comune(sil4, arh4, PAY_4K), "4KB"))
    if sil64:
        bucati.append(md_sil_vs_hil(comune(sil64, arh64, PAY_64K), "64KB"))
    scrie(os.path.join(out, "tabel_sil_vs_hil.md"), "\n".join(bucati))

    anom = toate_anomaliile(r4) + toate_anomaliile(r64)
    print("anomalii mecanice: %d" % len(anom))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
