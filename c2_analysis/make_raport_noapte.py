#!/usr/bin/env python3
"""make_raport_noapte.py -- genereaza c2_analysis/RAPORT_NOAPTE.md, NON-interactiv.

Ruleaza make_hil_tables + make_hil_figures pe datele reale, apoi coase raportul:
tabelele markdown asa cum au fost scrise in ANALIZA_C2, lista figurilor cu dimensiuni,
si sectiunea ANOMALII DETECTATE.

CE NU FACE, deliberat: NU interpreteaza stiintific. Nu scrie 'zenoh cedeaza la 30%' si nu
propune explicatii. Raportul e MECANIC (ce s-a generat, din ce, cat de mare) plus lista de
anomalii verificabile. Interpretarea o face omul, duminica dimineata, cu ochii lui.

ANOMALII cautate (mecanice, nu de continut), per repetitie:
  - mismatch summary-vs-CSV : campul 'n' din _summary.json != numarul de randuri din CSV;
  - first_seq < 11          : bench_client ignora 10 mesaje de incalzire, deci prima
                              secventa livrata nu poate fi sub 11;
  - n > sent                : mai multe esantioane primite decat trimise (imposibil).

READ-ONLY pe arhive. Scrie DOAR in ~/DATE_CAMPANIE/ANALIZA_C2/ (tabele+figuri) si in
c2_analysis/RAPORT_NOAPTE.md (in repo).

Uz:
  python3 make_raport_noapte.py                 # datele reale, regenereaza tot
  python3 make_raport_noapte.py --selftest
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_hil_tables as T
import make_hil_figures as F

AICI = os.path.dirname(os.path.abspath(__file__))
RAPORT = os.path.join(AICI, "RAPORT_NOAPTE.md")


def sectiune_anomalii(perechi_arhiva):
    """perechi_arhiva: [(eticheta, randuri)]. Intoarce (text_markdown, numar_total)."""
    out = ["## ANOMALII DETECTATE", ""]
    total = 0
    for eticheta, randuri in perechi_arhiva:
        anom = T.toate_anomaliile(randuri)
        total += len(anom)
        out.append("### %s" % eticheta)
        if not anom:
            out.append("")
            out.append("Niciuna. Verificate: mismatch summary-vs-CSV, first_seq<11, n>sent, "
                       "fisiere lipsa, JSON corupt -- pe fiecare repetitie din fiecare "
                       "celula.")
            out.append("")
            continue
        out.append("")
        out.append("| unde | ce |")
        out.append("|---|---|")
        for unde, ce in anom:
            out.append("| %s | %s |" % (unde, ce))
        out.append("")
    return "\n".join(out), total


def lista_figuri(caiuri):
    out = ["## FIGURI GENERATE", "",
           "| fisier | octeti |", "|---|---|"]
    for p in caiuri:
        out.append("| %s | %d |" % (os.path.relpath(p, os.path.dirname(os.path.dirname(p)))
                                    if os.path.dirname(p) else p, os.path.getsize(p)))
    out.append("")
    return "\n".join(out)


def citeste(cale):
    with open(cale) as f:
        return f.read().rstrip("\n")


def construieste(arh4, arh64, out_dir, caiuri_fig, stamp):
    """Coase raportul din bucatile deja scrise pe disc. Functie pura de I/O simplu."""
    r4, ex4 = T.tabel(arh4, T.PAY_4K)
    r64, ex64 = T.tabel(arh64, T.PAY_64K)
    anom_txt, anom_n = sectiune_anomalii([
        ("HIL 4KB (%s)" % os.path.basename(arh4), r4),
        ("HIL 64KB (%s)" % os.path.basename(arh64), r64)])
    # eticheta sarcinii utile e OBLIGATORIE: 'zenoh/ge_15_8' e moarta la 64KB dar are
    # supravietuitori la 4KB -- fara eticheta lista ar induce in eroare
    celule_moarte = ([("4KB", r["cond"], r["rmw"]) for r in r4 if r["n0"] == r["N"] and r["N"]]
                     + [("64KB", r["cond"], r["rmw"]) for r in r64
                        if r["n0"] == r["N"] and r["N"]])

    cap = [
        "# RAPORT NOAPTE -- campania HIL C2",
        "",
        "Generat NON-interactiv de `c2_analysis/make_raport_noapte.py` la %s." % stamp,
        "Raport MECANIC: ce s-a generat, din ce date, si ce anomalii verificabile exista.",
        "**Nu contine interpretare stiintifica** -- aceea ramane a ta.",
        "",
        "## SURSE (read-only, arhivele sunt sigilate a-w)",
        "",
        "| rol | cale |",
        "|---|---|",
        "| HIL 4KB | `%s` |" % arh4,
        "| HIL 64KB | `%s` |" % arh64,
        # referinta SIL 4KB e IMPARTITA (grila + combo): se listeaza toate arhivele
        "| SIL 4KB | %s |" % (", ".join("`%s`" % p for p in
                                        T.descopera_arhive(T.SIL_4K_TIPARE)) or "NEGASIT"),
        "| SIL 64KB | %s |" % (", ".join("`%s`" % p for p in
                                         T.descopera_arhive(T.SIL_64K_TIPARE)) or "NEGASIT"),
        "| iesiri | `%s` |" % out_dir,
        "",
        "Directoare-proba excluse explicit din tabele: %s."
        % (", ".join(sorted(set(sum(list(ex4.values()) + list(ex64.values()), []))))
           or "niciunul"),
        "",
        "## REZUMAT MECANIC",
        "",
        "- celule (conditie x RMW): %d la 4KB, %d la 64KB" % (len(r4), len(r64)),
        "- repetitii citite: %d la 4KB, %d la 64KB"
        % (sum(r["N"] for r in r4), sum(r["N"] for r in r64)),
        "- celule fara niciun supravietuitor (n0 = N): %d%s"
        % (len(celule_moarte),
           (" -- " + ", ".join("%s %s/%s" % (pay, rmw, c) for pay, c, rmw in celule_moarte))
           if celule_moarte else ""),
        "- anomalii mecanice: %d" % anom_n,
        "",
        "Statisticile din tabele sunt CONDITIONATE pe rularile supravietuitoare (n>0);",
        "fractia de esec e raportata separat ca n0=k/N. O celula cu n0=N nu are mediana --",
        "apare ca `-` in tabele si hasurata in figuri.",
        "",
    ]
    corp = [citeste(os.path.join(out_dir, "tabel_hil_4k.md")), "",
            citeste(os.path.join(out_dir, "tabel_hil_64k.md")), "",
            citeste(os.path.join(out_dir, "tabel_sil_vs_hil.md")), "",
            lista_figuri(caiuri_fig), anom_txt,
            "## FISIERE .TEX", "",
            "`tabel_hil_4k.tex` si `tabel_hil_64k.tex` sunt documente complete "
            "(article, tabular simplu, fara booktabs) -- se compileaza direct cu pdflatex.",
            ""]
    return "\n".join(cap + corp)


def _selftest():
    """Fara arhive reale: se verifica DOAR mecanica de coasere -- sectiunea de anomalii
    (cu si fara anomalii) si lista de figuri."""
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="raport_selftest_")
    try:
        curat = [{"cond": "ideal", "rmw": "zenoh", "N": 2, "n0": 0, "anomalii": []}]
        txt, n = sectiune_anomalii([("A", curat)])
        assert n == 0 and "Niciuna." in txt, txt
        murdar = [{"cond": "ge_15_8", "rmw": "zenoh", "N": 1, "n0": 0,
                   "anomalii": [("zenoh/ge_15_8/rep3", "n=10 > sent=5")]}]
        txt2, n2 = sectiune_anomalii([("A", curat), ("B", murdar)])
        assert n2 == 1 and "| zenoh/ge_15_8/rep3 | n=10 > sent=5 |" in txt2, txt2
        assert "### A" in txt2 and "### B" in txt2, txt2
        # lista de figuri: dimensiuni reale de pe disc
        fd = os.path.join(d, "fig")
        os.makedirs(fd)
        p = os.path.join(fd, "f.png")
        with open(p, "wb") as f:
            f.write(b"x" * 1234)
        lf = lista_figuri([p])
        assert "fig/f.png" in lf and "1234" in lf, lf
        print("SELFTEST make_raport_noapte OK (7 verificari).")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    arh4, arh64 = T.ARH_4K_DEFAULT, T.ARH_64K_DEFAULT
    out_dir = T.OUT_DEFAULT
    for a in (arh4, arh64):
        if not os.path.isdir(a):
            print("arhiva inexistenta: %s" % a)
            return 2
    print("[1/3] tabele...")
    if T.main([arh4, arh64, "--out", out_dir]) != 0:
        return 2
    print("[2/3] figuri...")
    caiuri = F.genereaza(arh4, arh64, os.path.join(out_dir, "fig"))
    print("[3/3] raport...")
    # timbrul de timp se ia din fisierele generate, nu din ceas: raportul descrie EXACT
    # artefactele de pe disc
    import datetime
    stamp = datetime.datetime.fromtimestamp(
        os.path.getmtime(os.path.join(out_dir, "tabel_hil_4k.md"))).strftime(
            "%Y-%m-%d %H:%M:%S")
    text = construieste(arh4, arh64, out_dir, caiuri, stamp)
    with open(RAPORT, "w") as f:
        f.write(text)
    print("  scris %s (%d octeti, %d randuri)"
          % (RAPORT, len(text.encode()), text.count("\n") + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
