#!/usr/bin/env python3
"""valideaza_instrument_c3.py -- sonda de canal masoara chiar ce injecteaza netem?

DE CE EXISTA
C2 are o sectiune de validare a instrumentului: inainte de a crede orice cifra de livrare,
s-a aratat cu o sonda UDP separata ca netem injecteaza chiar (L,B) cerute, si ca pierderea
la nivel de aplicatie e ALTCEVA (rezultat, nu calibrare). C3 are nevoie de simetricul ei,
fiindca intreaga contributie sta pe o presupunere: sonda de canal citeste marimea pe care e
indexata tabela de politica. Daca sonda ar minti, gateway-ul ar cauta in tabela cu o cheie
gresita si ar da raspunsuri gresite cu aer de rigoare.

Unealta asta NU ruleaza nimic. Citeste jurnalele deja scrise si pune fata in fata:
    (L, B) MASURAT   -- sonda_canal.csv, rapoartele reflectorului
    (L, B) INJECTAT  -- eticheta rularii (ex. 'ge_15_8' = L 15%, B 8)
Asta a fost si cerinta: comparatia trebuie sa se poata face offline, fara sa se repete
campania. Daca fisierele nu ajung pentru comparatie, atunci jurnalul e incomplet -- si asta
se afla ACUM, nu dupa ce masinile au fost demontate.

DISCIPLINA DE CITIRE (aceeasi ca la C2)
  - se raporteaza si rularile in care sonda NU a produs nimic (n0), separat, nu se
    strecoara in mediane;
  - medianele se calculeaza pe supravietuitori;
  - se folosesc DOAR rapoartele in care estimatorul chiar a convers. Flagul 'stabil' NU e
    destul: el devine adevarat dupa cateva goluri, cu mult inainte ca media exponentiala sa
    fi ajuns la valoarea de regim. Masurat pe testul de integrare: cu filtru doar pe
    'stabil', 30% injectat iesea 20.7% masurat -- si abaterea de 9.3 pp nu era a sondei, ci
    a rampei de convergenta amestecate in mediana.
    Pragul e DERIVAT, nu ales: EWMA cu alpha are constanta de timp 1/alpha esantioane, deci
    dupa N_CONSTANTE_TIMP constante biasul initial a scazut de e^5 ori (sub 1%).
        N_MIN_VALIDARE = N_CONSTANTE_TIMP / ALPHA_L = 5 / 0.01 = 500 esantioane

Uz:
  python3 tools/valideaza_instrument_c3.py <dir_rulare> [<dir_rulare> ...]
  python3 tools/valideaza_instrument_c3.py --selftest
Iesire: tabel pe stdout si, cu --json <cale>, acelasi continut ca date.
"""
import argparse
import csv
import json
import os
import re
import statistics as st
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AICI), "c3_gateway", "core"))
from estimator import ALPHA_L                                       # noqa: E402

N_CONSTANTE_TIMP = 5.0
N_MIN_VALIDARE = int(N_CONSTANTE_TIMP / ALPHA_L)

TIPAR_CONDITIE = re.compile(r"(?:^|_)ge_(\d+)_(\d+)(?:_|$)")
TIPAR_IDEAL = re.compile(r"(?:^|_)(ideal|clean|curat)(?:_|$)")


def conditie_injectata(eticheta):
    """(L_pct, B) din eticheta rularii, sau None daca eticheta nu spune.
    NU se ghiceste: o eticheta pe care n-o intelegem inseamna 'nu stiu ce s-a injectat',
    iar randul respectiv se raporteaza ca atare. Un ghicit tacut aici ar fabrica exact
    adevarul de referinta fata de care se valideaza instrumentul."""
    if not eticheta:
        return None
    m = TIPAR_CONDITIE.search(eticheta)
    if m:
        return float(m.group(1)), float(m.group(2))
    if TIPAR_IDEAL.search(eticheta):
        return 0.0, 1.0
    return None


def citeste_rulare(director):
    """Un jurnal de rulare -> dict cu ce trebuie pentru comparatie."""
    rez = {}
    cale_rez = os.path.join(director, "rezumat.json")
    if os.path.isfile(cale_rez):
        with open(cale_rez) as f:
            rez = json.load(f)
    rapoarte = []
    cale_sc = os.path.join(director, "sonda_canal.csv")
    if os.path.isfile(cale_sc):
        with open(cale_sc) as f:
            for r in csv.DictReader(f):
                try:
                    rapoarte.append({"t": float(r["t_mono"]), "L": float(r["L"]),
                                     "B": float(r["B"]), "n": int(r["n"]),
                                     "stabil": r["stabil"] == "1"})
                except (KeyError, ValueError):
                    continue
    return {
        "director": director,
        "nume": os.path.basename(os.path.normpath(director)),
        "eticheta": rez.get("eticheta", ""),
        "injectat": conditie_injectata(rez.get("eticheta", "")),
        "rapoarte": rapoarte,
        "rezumat": rez,
    }


def compara(rulare, n_min=N_MIN_VALIDARE):
    """Un rand de tabel. Intoarce si motivul cand nu se poate compara -- 'nu se poate'
    e un rezultat, nu o lipsa de rezultat."""
    r = dict(rulare)
    asezate = [x for x in rulare["rapoarte"] if x["stabil"] and x["n"] >= n_min]
    r["n_rapoarte"] = len(rulare["rapoarte"])
    r["n_asezate"] = len(asezate)
    r["n_min"] = n_min
    r["L_masurat"] = r["B_masurat"] = None
    r["dL_pp"] = r["dB"] = None
    r["L_min"] = r["L_max"] = None
    if not rulare["rapoarte"]:
        r["motiv"] = "n0: sonda de canal nu a produs niciun raport"
        return r
    if not asezate:
        r["motiv"] = ("niciun raport cu estimatorul convers (n >= %d); rularea a fost prea "
                      "scurta pentru validare" % n_min)
        return r
    Ls = [100.0 * x["L"] for x in asezate]
    r["L_masurat"] = st.median(Ls)
    r["B_masurat"] = st.median([x["B"] for x in asezate])
    # Imprastierea INTRA-rulare, nu ca decor: la B mare informatia despre L vine per RAFALA,
    # nu per pachet. La L=30%, B=8, cele 500 de esantioane ale pragului de convergenta
    # contin doar ~19 rafale, deci estimarea are variatie mare chiar dupa ce biasul a
    # disparut. O singura rulare NU poate valida instrumentul; de aceea se raporteaza si
    # min/max, ca cifra din mijloc sa nu para mai sigura decat e.
    r["L_min"], r["L_max"] = min(Ls), max(Ls)
    if rulare["injectat"] is None:
        r["motiv"] = "eticheta '%s' nu spune ce s-a injectat" % rulare["eticheta"]
        return r
    Li, Bi = rulare["injectat"]
    r["dL_pp"] = r["L_masurat"] - Li
    r["dB"] = r["B_masurat"] - Bi
    r["motiv"] = ""
    return r


def tipareste(randuri):
    print("%-22s %-10s %-14s %-14s %-9s %-8s %s"
          % ("rulare", "eticheta", "injectat (L%,B)", "masurat (L%,B)", "dL (pp)", "dB",
             "rapoarte"))
    print("-" * 100)
    n0, comparabile = [], []
    for r in randuri:
        inj = "-" if r["injectat"] is None else "%.0f / %.0f" % r["injectat"]
        mas = ("-" if r["L_masurat"] is None
               else "%.2f / %.2f" % (r["L_masurat"], r["B_masurat"]))
        dl = "-" if r["dL_pp"] is None else "%+.2f" % r["dL_pp"]
        db = "-" if r["dB"] is None else "%+.2f" % r["dB"]
        imp = ("" if r.get("L_min") is None
               else "  [L in %.1f..%.1f]" % (r["L_min"], r["L_max"]))
        print("%-22s %-10s %-14s %-14s %-9s %-8s %d (%d converse)%s%s"
              % (r["nume"][:22], r["eticheta"][:10], inj, mas, dl, db,
                 r["n_rapoarte"], r["n_asezate"], imp,
                 "  <- " + r["motiv"] if r["motiv"] else ""))
        if r["dL_pp"] is None:
            n0.append(r)
        else:
            comparabile.append(r)
    print()
    print("Rulari comparabile: %d. Rulari fara comparatie: %d (raportate separat, NU intra "
          "in mediane)." % (len(comparabile), len(n0)))
    if comparabile:
        dl = [r["dL_pp"] for r in comparabile]
        db = [r["dB"] for r in comparabile]
        print("Abaterea sondei fata de ce s-a injectat, pe supravietuitori:")
        print("  dL: mediana %+.2f pp, min %+.2f, max %+.2f" % (st.median(dl), min(dl),
                                                                max(dl)))
        print("  dB: mediana %+.2f, min %+.2f, max %+.2f" % (st.median(db), min(db),
                                                             max(db)))
        print()
        print("Cum se citeste: o abatere mica si FARA structura (nu creste cu L, nu depinde")
        print("de transportul activ) inseamna ca sonda masoara canalul, nu transportul --")
        print("ceea ce e chiar premisa pe care sta tabela de politica. O abatere care depinde")
        print("de transportul activ ar insemna ca sonda nu e transport-neutra si ca toata")
        print("corectia de la etapa 3.5 nu si-a atins scopul.")
        if len(comparabile) < 3:
            print()
            print("ATENTIE: %d rulare(i) comparabila(e). Cifrele de mai sus arata ce a vazut"
                  % len(comparabile))
            print("sonda, dar NU valideaza inca instrumentul: la B mare estimarea variaza")
            print("mult de la o rulare la alta (informatia vine per rafala). Concluzia de")
            print("validare se trage pe repetitiile campaniei, nu pe o rulare.")
    return 0 if comparabile else 1


def _selftest():
    import shutil
    import tempfile

    # 1. citirea etichetei: ce se intelege si, mai important, ce NU se ghiceste
    assert conditie_injectata("ge_15_8") == (15.0, 8.0)
    assert conditie_injectata("C3_ge_30_3_rulare2") == (30.0, 3.0)
    assert conditie_injectata("ideal") == (0.0, 1.0)
    assert conditie_injectata("rulare") is None, "eticheta neinteligibila NU se ghiceste"
    assert conditie_injectata("") is None
    assert conditie_injectata("delay_50ms") is None
    assert N_MIN_VALIDARE == 500, N_MIN_VALIDARE

    d = tempfile.mkdtemp(prefix="valid_c3_")
    try:
        # 2. o rulare completa: mediana se ia pe rapoartele ASEZATE, nu pe toate.
        # Fixture-ul e construit tocmai ca cele doua raspunsuri sa difere: tranzitoriul e
        # la 2%, regimul la ~15%. Daca cineva sterge filtrul pe 'stabil', testul pica.
        r1 = os.path.join(d, "C3_ge_15_8_r1")
        os.makedirs(r1)
        with open(os.path.join(r1, "rezumat.json"), "w") as f:
            json.dump({"eticheta": "ge_15_8"}, f)
        with open(os.path.join(r1, "sonda_canal.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_mono", "L", "B", "n", "goluri", "stabil"])
            for i in range(5):
                w.writerow([i * 0.5, 0.02, 1.1, 50 + i, 2, 0])       # tranzitoriu (stabil=0)
            for i in range(4):
                # stabil=1 DAR inca neconvers (n mic): filtrul pe 'stabil' singur le-ar lua
                w.writerow([5 + i * 0.5, 0.05, 2.0, 80 + i, 8, 1])
            for i in range(9):
                w.writerow([10 + i * 0.5, 0.148 + 0.001 * i, 7.8, 500 + i, 70, 1])
        # 3. o rulare in care sonda a tacut: n0, raportat separat
        r2 = os.path.join(d, "C3_ge_30_8_r1")
        os.makedirs(r2)
        with open(os.path.join(r2, "rezumat.json"), "w") as f:
            json.dump({"eticheta": "ge_30_8"}, f)
        with open(os.path.join(r2, "sonda_canal.csv"), "w", newline="") as f:
            csv.writer(f).writerow(["t_mono", "L", "B", "n", "goluri", "stabil"])

        randuri = [compara(citeste_rulare(x)) for x in (r1, r2)]
        a, b = randuri
        assert abs(a["L_masurat"] - 15.2) < 1e-6, a["L_masurat"]   # mediana pe cele 9
        assert abs(a["dL_pp"] - 0.2) < 1e-6, a["dL_pp"]
        assert a["n_rapoarte"] == 18 and a["n_asezate"] == 9, a
        # cele 4 rapoarte stabile-dar-neconverse (L=5%) NU au voie sa intre in mediana:
        # daca ar intra, L_masurat ar cadea sub 15 si validarea ar acuza sonda de un bias
        # care e de fapt rampa estimatorului
        assert a["L_masurat"] > 15.0, a["L_masurat"]
        assert a["L_min"] is not None and a["L_max"] >= a["L_min"], a
        assert a["L_min"] <= a["L_masurat"] <= a["L_max"], a
        assert b["dL_pp"] is None and "n0" in b["motiv"], b
        # n0 NU are voie sa intre in mediana: daca ar intra, ar cobori-o spre 0
        comparabile = [r for r in randuri if r["dL_pp"] is not None]
        assert len(comparabile) == 1, comparabile

        # 4. eticheta neinteligibila: masurat exista, comparatia nu -- si se spune de ce
        r3 = os.path.join(d, "C3_altceva")
        os.makedirs(r3)
        with open(os.path.join(r3, "rezumat.json"), "w") as f:
            json.dump({"eticheta": "rulare"}, f)
        with open(os.path.join(r3, "sonda_canal.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_mono", "L", "B", "n", "goluri", "stabil"])
            w.writerow([1.0, 0.1, 2.0, 600, 40, 1])
        c = compara(citeste_rulare(r3))
        assert c["L_masurat"] is not None and c["dL_pp"] is None, c
        assert "nu spune" in c["motiv"], c

        # 5. un director fara jurnal de sonda nu arunca exceptie, ci devine n0
        r4 = os.path.join(d, "C3_gol")
        os.makedirs(r4)
        e = compara(citeste_rulare(r4))
        assert e["dL_pp"] is None and e["n_rapoarte"] == 0, e
        print("SELFTEST valideaza_instrument_c3 OK (eticheta, mediana pe asezate, n0 "
              "separat, eticheta neinteligibila nu se ghiceste).")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main(argv):
    ap = argparse.ArgumentParser(description="Validarea de instrument pentru C3.")
    ap.add_argument("rulari", nargs="*", help="directoare de jurnal (--jurnal al rularii)")
    ap.add_argument("--json", default=None, help="scrie si datele, nu doar tabelul")
    ap.add_argument("--n-min", type=int, default=N_MIN_VALIDARE,
                    help="esantioane minime pentru a considera estimatorul convers "
                         "(implicit %d = %.0f constante de timp)"
                         % (N_MIN_VALIDARE, N_CONSTANTE_TIMP))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        _selftest()
        return 0
    if not a.rulari:
        print(__doc__.strip())
        return 0
    randuri = [compara(citeste_rulare(x), a.n_min) for x in a.rulari]
    print("Prag de convergenta: n >= %d esantioane (%.0f constante de timp la alpha=%.3f)\n"
          % (a.n_min, N_CONSTANTE_TIMP, ALPHA_L))
    cod = tipareste(randuri)
    if a.json:
        with open(a.json, "w") as f:
            json.dump([{k: v for k, v in r.items() if k not in ("rapoarte", "rezumat")}
                       for r in randuri], f, indent=1)
        print("\nscris: %s" % a.json)
    return cod


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
